# -*- coding: utf-8 -*-
"""
Contains various functions for debarcoding
@author: mleutenegger
"""
import pandas as pd
import numpy as np

NAME_BARCODE = 'barcode'
NAME_INVALID = 'invalid'
NAME_WELLCOLUMN = 'well'

def debarcode(data, bc_key, dist = 30):
    """
    Debarcode a Dataframe from the image data.

    Args:
        DataFrame plot_cells:   the image data from cellprofiler, prepared as usual (improve doc)
        DataFrame bc_key:       the barcoding key. The column indexes should specify the metal
                                column in plot_cells. the well column MUST be designated
                                by 'well'.
        int dist:               the distance until which the cells should be considered
                                for barcoding.

    Returns:
        dictionary {imageNumber => well}
    """

    data = data.copy()
    data = _treshold_data(data)
    data = _debarcode_data(bc_key, data)
    bc_dic = _summarize_singlecell_barcodes(data)
    data = data.drop('present', axis=1)
    
    return bc_dic, data

def _treshold_data(bc_dat):
    bc_dat = bc_dat.copy()
    bc_dat = bc_dat.apply(lambda x: (x-np.mean(x))/np.std(x),)
    bc_dat[bc_dat > 0] = 1
    bc_dat[bc_dat < 0] = 0
    return bc_dat

def _debarcode_data(bc_key, bc_dat):
    tab_bc = bc_key.set_index(NAME_WELLCOLUMN)
    metals = list(tab_bc.columns)
    tab_bc[NAME_BARCODE] = tab_bc.apply(lambda x: ''.join([str(int(v)) for v in x]),axis=1)
    tab_bc = tab_bc.reset_index(drop=False)
    bc_dict = {row[NAME_BARCODE]: row[NAME_WELLCOLUMN] for idx, row in tab_bc.iterrows()}


    data = bc_dat.loc[:, metals].copy()
    data = data.rename(columns={chan: ''.join(c for c in chan if c.isdigit()) for chan in data.columns})
    data[NAME_BARCODE] = data.apply(lambda x: ''.join([str(int(v)) for v in x]),axis=1)
    data[NAME_WELLCOLUMN] = [bc_dict.get(b, NAME_INVALID) for b in data[NAME_BARCODE]]

    data= data.set_index(NAME_WELLCOLUMN, append=True)
    data= data.set_index(NAME_BARCODE, append=True)

    data['count'] = 1

    data = data.loc[data.index.get_level_values(NAME_WELLCOLUMN) != '' ,'count']
    data = data.reset_index(drop=False, level=[NAME_WELLCOLUMN, NAME_BARCODE], name='present')
    return data

def _summarize_singlecell_barcodes(data):
    # prepare a dicitionary containing the barcode
    idxs = data.index.get_level_values('ImageNumber').unique()
    dic = pd.DataFrame(columns=[
        'well',
        'valid_bcs',
        'invalid_bcs',
        'highest_bc_count',
        'second_bc_count'
    ], index=idxs)


    for imagenr in idxs:
        temp = dict()
        summary = data.xs(imagenr, level='ImageNumber')[NAME_WELLCOLUMN].value_counts()
        try:
            temp['invalid_bcs']=summary[NAME_INVALID]
            del(summary[NAME_INVALID])
        except KeyError:
            temp['invalid_bcs']=0
        temp['well']=summary.keys()[0]
        temp['valid_bcs']=summary.sum()
        temp['highest_bc_count']=summary[temp['well']]
        if len(summary) > 1:
            temp['second_bc_count']=summary[summary.keys()[1]]
        else:
            temp['second_bc_count']=0
        dic.loc[imagenr]= temp
    return dic

