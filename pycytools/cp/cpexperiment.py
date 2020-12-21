# %%
import matplotlib.pyplot as plt  # '3.3.2'
import numpy as np  # '1.19.1'
import pandas as pd  # '1.1.2'
import scanpy as sp  # '1.6.0'

import pycytools.cp.io as cpio
import pycytools.cp.objectrelations as objrel
import pycytools.library as lib
import pycytools.plots as plth
from pycytools.cp.vars import COL_DATATYPE, COL_COLUMN_NAME, IS_FLOAT, IMAGE_ID, IMAGE_NUMBER, OBJECT_ID, OBJECT_NUMBER, \
    OBJECT_MASK_NAME, RUN, COL_SCALING, FEATURE_NAME, IMAGE_NAME, OBJECT_NAME, CHANNEL


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


def scale_measurements(ad_obj, ad_img):
    for imgname, g in ad_obj.var.loc[~ad_obj.var[IMAGE_NAME].isna(), :].groupby(IMAGE_NAME):
        v = ad_img.var.query(f'{IMAGE_NAME} == "{imgname}" & {FEATURE_NAME} == "{COL_SCALING}"')
        if len(v.index) > 0:
            scaling = ad_img.obs_vector(v.index[0])
            assert np.allclose(scaling, scaling[
                0]), "Not all images scaled equal! Scaling currently not implemented for this case."
            ad_obj[:, g.index].X = ad_obj[:, g.index].X * scaling[0]


def make_columns_categorical(dat, categorydict):
    for k, cats in categorydict.items():
        dat[k] = pd.Categorical(dat[k], categories=cats)


class CellprofilerExperiment:

    def __init__(self, run, fn_images, fn_images_var,
                 default_imagename=None):
        self.run = run
        self.objects = {}
        self.obj_rel = None
        self.ioh = None
        self.ad_img = self._get_ad_img(run, fn_images, fn_images_var)
        self.default_imagename = default_imagename
        self.default_objectname = None

    @staticmethod
    def _get_ad_img(run, fn_images, fn_images_var):
        ad_img = get_ad_img(pd.read_csv(fn_images), pd.read_csv(fn_images_var), run)
        ad_img.obs[RUN] = run
        return ad_img

    def add_object(self, fn_object, fn_object_var, object_name,
                   object_mask_name=None, is_default=False):
        ad_object = get_ad_obj(pd.read_csv(fn_object), pd.read_csv(fn_object_var), run=self.run,
                               object_name=object_name, object_mask_name=object_mask_name)
        scale_measurements(ad_object, self.ad_img)
        self.objects[object_name] = ad_object
        if is_default:
            self.default_objectname = object_name
        return self

    @property
    def default_mask(self):
        return self.objects[self.default_objectname].uns[OBJECT_MASK_NAME]

    def add_iohelper(self, fol_images, fol_masks):
        ioh = cpio.IoHelper(self.ad_img.obs,
                            fol_images=fol_images,
                            fol_masks=fol_masks,
                            default_image=self.default_imagename,
                            default_mask=self.default_mask)
        self.ioh = ioh
        return self

    def add_object_relations(self, fn_relations):
        self.obj_rel = objrel.ObjectRelations(pd.read_csv(fn_relations))

    def merge_img_meta(self, dat, meta_cols=(RUN,)):
        dat = dat.merge(self.ad_img.obs[list(meta_cols)], how='left', left_on='ImageId', right_index=True)
        return dat

    def get_plot_data(self, var_names, object_name=None, img_meta_cols=('run')):
        ad_lab = self.objects[object_name]
        pdat = (ad_lab.obs
                .join(pd.DataFrame(ad_lab[:, var_names].X, columns=var_names, index=ad_lab.obs.index))
                )
        if img_meta_cols is not None:
            pdat = self.merge_img_meta(pdat, meta_cols=img_meta_cols)
        return pdat

    def plot_imag_ad(self, ad, figsize=None, add_colorbar=True,
                     bad_alpha=0, ax=None,
                     **kwargs):
        """
        Plots all objects contained in the anndata, plotting the individual images as columns.

        :param ad: an anndata with obs variables: 'image_id', 'object_type', 'object_number'
        :param chan: The channel (metal) to plot
        :param figsize: the output image size

        :returns: the figure object
        """
        assert ad.X.shape[1] == 1, "Subset the anndata until it has at most 1 value"
        imgids = ad.obs['ImageId'].unique()
        if ax is None:
            fig, axs = plt.subplots(ncols=len(imgids), figsize=figsize)
        else:
            assert len(imgids) == 1
            axs = [ax]
        try:
            len(axs)
        except TypeError:
            axs = [axs]
        object_name = ad.uns[OBJECT_NAME]
        for ax, (imid, dat) in zip(axs, ad.obs.groupby([IMAGE_ID])):
            mask = self.ioh.get_mask(imid, mask_name=object_name)
            values = ad[dat.index, :].X.squeeze()
            labels = dat[OBJECT_NUMBER]
            img = lib.map_series_on_mask(mask, labels, values)

            colorbar = (ax == axs[-1]) and add_colorbar
            plth.plot_heatmask(img, ax=ax, colorbar=colorbar, bad_alpha=bad_alpha, **kwargs)
            ax.axis('off')
        plth.adapt_ax_clims(axs)
        return axs
