# -*- coding: utf-8 -*-
"""
Contains various functions for debarcoding
@author: mleutenegger
"""

def debarcode(plot_cells, bc_key, dist = 30):
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

    # prepare a dicitionary containing the barcode
    tab_bc = bc_key.set_index('well')
    order = tab_bc.columns
    tab_bc['barcode'] = tab_bc.apply(lambda x: ''.join([str(int(v)) for v in x]),axis=1)
    tab_bc = tab_bc.reset_index(drop=False)
    bc_dict = {row['barcode']: row['well'] for idx, row in tab_bc.iterrows()}

    dic = pd.DataFrame(columns=[
        'ImageNumber',
        'well',
        'valid_bcs',
        'invalid_bcs',
        'highest_bc_count',
        'second_bc_count'
    ])
    amb_fil = plot_cells['filter','is-ambiguous'] == False

    data = plot_cells['MeanIntensity'].loc[(plot_cells[('MeanIntensity','dist-rim')] < dist) & amb_fil, :]
    data = data[order]
    data = data.apply(lambda x: (x-np.mean(x))/np.std(x),)
    data[data > 0] = 1
    data[data < 0] = 0
    data = data.rename(columns={chan: ''.join(c for c in chan if c.isdigit()) for chan in data.columns})
    data['barcode'] = data[bcmass].apply(lambda x: ''.join([str(int(v)) for v in x]),axis=1)
    data['well'] = [bc_dict.get(b, 'invalid') for b in data['barcode']]

    data= data.set_index('well', append=True)
    data= data.set_index('barcode', append=True)

    data['count'] = 1

    data = data.loc[data.index.get_level_values('well') != '' ,'count']
    data = data.reset_index(drop=False, level=['well', 'barcode'], name='present')

    for imagenr in data.index.get_level_values('ImageNumber').unique():
        temp = {
            'ImageNumber':int(imagenr)
        }
        summary = data.xs(imagenr, level='ImageNumber')['well'].value_counts()
        try:
            temp['invalid_bcs']=summary['invalid']
            del(summary['invalid'])
        except KeyError:
            temp['invalid_bcs']=0
        temp['well']=summary.keys()[0]
        temp['valid_bcs']=summary.sum()
        temp['highest_bc_count']=summary[temp['well']]
        if len(summary) > 1:
            temp['second_bc_count']=summary[summary.keys()[1]]
        else:
            temp['second_bc_count']='0'
        dic.loc[len(dic)]= temp

    dic['ImageNumber'] = dic['ImageNumber'].apply(lambda x: int(x))
    return dic
