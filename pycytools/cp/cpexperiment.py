# %%
import pathlib
import warnings

import numpy as np  # '1.19.1'
import pandas as pd  # '1.1.2'
import scanpy as sp  # '1.6.0'

import pycytools.cp.io as cpio
import pycytools.cp.objectrelations as objrel
from pycytools.cp.vars import COL_DATATYPE, COL_COLUMN_NAME, IS_FLOAT, IMAGE_ID, IMAGE_NUMBER, OBJECT_ID, OBJECT_NUMBER, \
    OBJECT_MASK_NAME, RUN, COL_SCALING, FEATURE_NAME, IMAGE_NAME, OBJECT_NAME, CHANNEL, CHANNEL_ID


def cp_to_ad(dat_meas, dat_var):
    """
    Converts cellprofiler output to anndata
    """
    var = dat_var.query(f'{COL_DATATYPE} == "{IS_FLOAT}"')
    var = var.set_index(COL_COLUMN_NAME)
    obs = dat_meas.drop(columns=var.index)
    x = dat_meas[var.index]
    ad = sp.AnnData(x, obs=obs, var=var)
    return ad


def add_image_id(ad, run):
    """
    Adds an image id column
    """
    ad.obs[IMAGE_ID] = ad.obs[IMAGE_NUMBER].map(lambda x: f'{run}_{x}')


def add_obj_id(ad, object_name):
    """
    Adds an object id column
    """
    ad.obs[OBJECT_ID] = ad.obs.apply(lambda row: f'{row[IMAGE_ID]}_{object_name}_{row[OBJECT_NUMBER]}', axis=1)


def get_ad_img(dat_meas, dat_var, run='run1'):
    """
    Converts the image metadata table
    """
    ad = cp_to_ad(dat_meas, dat_var)
    add_image_id(ad, run=run)
    ad.obs = ad.obs.set_index(IMAGE_ID)
    return ad


def get_ad_obj(dat_meas, dat_var, run='run1', object_name='obj',
               object_mask_name=None):
    """
    Converts an object metadata table
    """
    if object_mask_name is None:
        object_mask_name = object_name
    ad = cp_to_ad(dat_meas, dat_var)
    ad.var[CHANNEL] = ad.var[CHANNEL].fillna(1)
    add_image_id(ad, run=run)
    add_obj_id(ad, object_name=object_name)
    ad.obs = ad.obs.set_index(OBJECT_ID)
    ad.uns[OBJECT_NAME] = object_name
    ad.uns[OBJECT_MASK_NAME] = object_mask_name
    return ad


def scale_measurements(ad_obj, ad_img, img_parent_dict=None):
    if img_parent_dict is None:
        img_parent_dict = {}
    for imgname, g in ad_obj.var.loc[~ad_obj.var[IMAGE_NAME].isna(), :].groupby(IMAGE_NAME):
        img_parent = img_parent_dict.get(imgname, imgname)
        v = ad_img.var.query(f'{IMAGE_NAME} == "{img_parent}" & {FEATURE_NAME} == "{COL_SCALING}"')
        if len(v.index) > 0:
            scaling = ad_img.obs_vector(v.index[0])
            assert np.allclose(scaling, scaling[
                0]), "Not all images scaled equal! Scaling currently not implemented for this case."
            ad_obj[:, g.index].X = ad_obj[:, g.index].X * scaling[0]
        else:
            warnings.warn(f'No scale found for {img_parent}.\n'
                          'Either this image is really unscaled or it is a\n'
                          'derived image that needs to be registered with its parent via the\n'
                          'img_parent_dict')


def make_columns_categorical(dat, categorydict):
    for k, cats in categorydict.items():
        dat[k] = pd.Categorical(dat[k], categories=cats)


class CellprofilerExperiment:

    def __init__(self, run, fn_images, fn_images_var,
                 img_parent_dict=None):
        self.run = run
        self.objects = {}
        self.obj_rel = None
        self.ioh = None
        self.panel = None
        self.ad_img = self._get_ad_img(run, fn_images, fn_images_var)
        if img_parent_dict is None:
            img_parent_dict = {}
        self.img_parent_dict = img_parent_dict

    @staticmethod
    def _get_ad_img(run, fn_images, fn_images_var):
        ad_img = get_ad_img(pd.read_csv(fn_images), pd.read_csv(fn_images_var), run)
        ad_img.obs[RUN] = run
        return ad_img

    def add_panel(self, fn_panel, col_channel):
        panel = pd.read_csv(fn_panel)
        panel[CHANNEL_ID] = panel[col_channel]
        panel = panel.drop(columns=CHANNEL, errors='ignore')
        self.panel = panel
        return self

    def add_object(self, fn_object, fn_object_var, object_name,
                   object_mask_name=None):
        ad_object = get_ad_obj(pd.read_csv(fn_object), pd.read_csv(fn_object_var), run=self.run,
                               object_name=object_name, object_mask_name=object_mask_name)
        scale_measurements(ad_object, self.ad_img, img_parent_dict=self.img_parent_dict)
        self.objects[object_name] = ad_object
        return self

    def get_mask_name(self, objectname):
        return self.objects[objectname].uns[OBJECT_MASK_NAME]

    def add_iohelper(self, fol_images, fol_masks, default_image_name=None,
                     default_object_name=None):

        if default_object_name is None:
            mask_name = None
        else:
            mask_name = self.get_mask_name(default_object_name)
        ioh = cpio.IoHelper(self.ad_img.obs,
                            fol_images=fol_images,
                            fol_masks=fol_masks,
                            default_image=default_image_name,
                            default_mask=mask_name)
        self.ioh = ioh
        return self

    def add_object_relations(self, fn_relations):
        self.obj_rel = objrel.ObjectRelations(pd.read_csv(fn_relations))

    def merge_img_meta(self, dat, meta_cols=(RUN,)):
        dat = dat.merge(self.ad_img.obs[list(meta_cols)], how='left', left_on='ImageId', right_index=True)
        return dat

    def get_data_frame(self, var_names, object_name=None, img_meta_cols=('run')):
        ad_lab = self.objects[object_name]
        pdat = (ad_lab.obs
                .join(pd.DataFrame(ad_lab[:, var_names].X, columns=var_names, index=ad_lab.obs.index))
                )
        if img_meta_cols is not None:
            pdat = self.merge_img_meta(pdat, meta_cols=img_meta_cols)
        return pdat

    def extend_var_with_panel(self, var):
        idx_name = var.index.name
        return (var.reset_index(drop=False)
                .merge(self.panel, on=CHANNEL_ID, how='left',
                       suffixes=('', '_panel'))
                .set_index(idx_name)
                )

    @classmethod
    def from_imcsegpipe_cpout(cls, fol_cpout, name,
                              col_channel='Metal Tag'):
        fol_base = pathlib.Path(fol_cpout)
        fn_cell = fol_base / 'cell.csv'
        fn_img = fol_base / 'Image.csv'

        fn_cell_var = fol_base / 'var_cell.csv'
        fn_img_var = fol_base / 'var_Image.csv'

        fol_images = fol_base / 'images'
        fol_masks = fol_base / 'masks'
        img_parents = {'FullStackFiltered': 'FullStack',
                       'FullStackComp': 'FullStack',
                       'ProbSegmentation': 'ProbabStack'}

        fn_panel = fol_base / 'panel.csv'
        col_channel = col_channel
        cpe = (cls(name, fn_images=fn_img,
                   fn_images_var=fn_img_var, img_parent_dict=img_parents)
               .add_object(fn_cell, fn_cell_var, object_name='cell',
                           object_mask_name='CellImage')
               .add_iohelper(fol_images, fol_masks,
                             default_image_name='FullStackFiltered',
                             default_object_name='cell')
               .add_panel(fn_panel, col_channel)
               )
        return cpe
