import pathlib
from collections import namedtuple

import numpy as np
import pandas as pd
import skimage.measure as skmeasure
from scipy import spatial

import pycytools.cp.cpexperiment as cpe
import pycytools.cp.segvars as segvars
import pycytools.cp.vars
import pycytools.cp.vars as cpvars
import pycytools.library as lib

V = segvars


class SegmentationData(cpe.CellprofilerExperiment):
    LABELS = 'Label'
    LABELS_MASK = 'LabelObjImg'
    CELLMASK = 'Mask2x'
    CELLMASK_MASK = 'Mask2xImg'

    def __init__(self, run, fn_images, fn_images_var):
        super().__init__(run, fn_images, fn_images_var)
        self.ad_lab = None
        self.ad_mask = None

    @staticmethod
    def _get_ad_img(run, fn_images, fn_images_var):
        ad_img = cpe.CellprofilerExperiment._get_ad_img(run, fn_images, fn_images_var)
        re_meta = '(?P<cropname>.*)_(?P<segimage>.*)-(?P<segsettings>.*)'
        ad_img.obs = ad_img.obs.join(lib.map_group_re(ad_img.obs['Metadata_base'], re_meta))
        return ad_img

    def add_label_meas(self, fn_labels, fn_labels_var):
        super().add_object(fn_labels, fn_labels_var, self.LABELS, self.LABELS_MASK)
        ad_lab = self.objects[self.LABELS]
        ad_lab.obs['label_codes'] = ad_lab.obs_vector(V.label_meas).astype('int') - 1
        ad_lab.obs['label'] = pd.Categorical.from_codes(ad_lab.obs['label_codes'],
                                                        categories=['center', 'border', 'background'])
        self.ad_lab = ad_lab
        return self

    def add_cellmask_meas(self, fn_cellmask, fn_cellmask_var):
        super().add_object(fn_cellmask, fn_cellmask_var, self.CELLMASK, self.CELLMASK_MASK)
        self.ad_mask = self.objects[self.CELLMASK]
        return self

    # data handling
    def get_plot_data(self, var_names, img_meta_cols=('cropname', 'segimage', 'segsettings', 'run'),
                      object_name=None):
        if object_name is None:
            object_name = self.LABELS
        ad_lab = self.objects[object_name]
        pdat = (ad_lab.obs
                .join(pd.DataFrame(ad_lab[:, var_names].X, columns=var_names, index=ad_lab.obs.index))
                )
        if img_meta_cols is not None:
            pdat = self.merge_img_meta(pdat, meta_cols=img_meta_cols)
        return pdat

    def add_percent_touching(self):
        """
        Adds the minimal percent touching of the mask bellow the label.
        This can be used to remove border labels that may introduce a bias how far cells
        are expanded into the 'background' area.
        """
        objr = self.obj_rel
        x = objr.get_vars_via_rel(pycytools.cp.vars.PARENT, ['Neighbors_PercentTouching_Adjacent'], 'Label',
                                  self.ad_lab.obs,
                                  self.CELLMASK,
                                  self.get_plot_data(['Neighbors_PercentTouching_Adjacent'],
                                                     img_meta_cols=None,
                                                     object_name=self.CELLMASK)

                                  )
        self.ad_lab.obs = self.ad_lab.obs.join(x.groupby('ObjectId').min(), how='left')

    def get_img_nbcenters(self, image_id, distance=25):
        hit = namedtuple('hit', [cpvars.FIRST_OBJ_NUMBER, cpvars.SECOND_OBJ_NUMBER, 'points', 'contains_border'])
        mask = self.ioh.get_mask(image_id, self.LABELS_MASK)
        dat_obj = self.ad_lab.obs.query(f'{cpvars.IMAGE_ID} == "{image_id}"')[[cpvars.OBJ_NUMBER, segvars.label]]
        dat = (pd.DataFrame(skmeasure.regionprops_table(mask, properties=('label', 'coords', 'centroid')))
               .rename(columns={'label': cpvars.OBJ_NUMBER})
               .merge(dat_obj)
               )
        dat_center = dat.query(f'{segvars.label} == "center"')
        dat_border = dat.query(f'{segvars.label} == "border"')

        if dat_border.shape[0] > 0:
            coords_border = np.vstack(dat_border['coords'])
        else:
            coords_border = []

        point_tree = spatial.cKDTree(dat_center[['centroid-0', 'centroid-1']].values)
        hit_list = []

        for i, (_, query_row) in enumerate(dat_center.iterrows()):
            pts = point_tree.query_ball_point(query_row[['centroid-0', 'centroid-1']], distance)
            pts = [p for p in pts if p > i]
            if len(pts) == 0:
                continue
            dat_hits = dat_center.iloc[pts, :]
            for _, row in dat_hits.iterrows():
                x = np.vstack([query_row.coords, row.coords])
                if len(x) < 4:
                    continue
                else:
                    conv_h = spatial.ConvexHull(x)
                    hull = conv_h.points[conv_h.vertices]

                d = spatial.Delaunay(hull)
                if len(coords_border) > 0:
                    has_border = np.any(d.find_simplex(coords_border) >= 0)
                else:
                    has_border = False
                hit_list.append(hit(query_row['ObjectNumber'], row['ObjectNumber'], d.points, has_border))
        return pd.DataFrame(hit_list)

    def add_center_rel(self, distance=25):
        crops = self.ad_img.obs[segvars.cropname].drop_duplicates()
        imgs = crops.index
        res = (pd.concat([self.get_img_nbcenters(i, distance=distance) for i in imgs], keys=crops)
               .reset_index(segvars.cropname, drop=False))
        dat = (res
               .merge(self.ad_img.obs[[segvars.cropname, cpvars.IMAGE_NUMBER]])
               .assign(**{cpvars.FIRST_IMG_NUMBER: lambda x: x[cpvars.IMAGE_NUMBER],
                          cpvars.SECOND_IMG_NUMBER: lambda x: x[cpvars.IMG_NUMBER],
                          cpvars.FIRST_OBJ_NAME: self.LABELS,
                          cpvars.SECOND_OBJ_NAME: self.LABELS})
               .drop(columns=[segvars.cropname, cpvars.IMAGE_NUMBER])
               )
        self.obj_rel.add_relationship(f'nbcenter_dist{int(distance)}', dat)

    def get_center_rel(self, distance=25):
        return self.obj_rel.get_vars_from_rel(f'nbcenter_dist{distance}',
                                              value_vars=['points', 'contains_border'],
                                              objectname=self.LABELS,
                                              dat=self.ad_lab.obs)

    def get_is_undersegmented(self, distance=25):
        center_rel = f'nbcenter_dist{distance}'
        if center_rel not in self.obj_rel.relations:
            self.add_center_rel(distance)
        dat = self.get_plot_data(['Intensity_MedianIntensity_Mask2xImg'])
        dat_nb_int = self.obj_rel.get_vars_via_rel(f'nbcenter_dist{distance}',
                                                   value_vars=['Intensity_MedianIntensity_Mask2xImg'],
                                                   rel_vars=['points', 'contains_border'],
                                                   objectname_1=self.LABELS,
                                                   dat_1=dat)
        dat_us = dat.join(dat_nb_int, rsuffix='_2', how='inner')
        dat_us['is_undersegmented'] = dat_us.eval(
            'Intensity_MedianIntensity_Mask2xImg == Intensity_MedianIntensity_Mask2xImg_2')
        return dat_us[['is_undersegmented', 'points', 'contains_border']]

    def get_is_oversegmented(self):
        dat = (self.get_plot_data(['Intensity_MinIntensity_MaskDistance'])
               .query('label == "center"')
               )
        dat['is_oversegmented'] = dat['Intensity_MinIntensity_MaskDistance'] < 0
        return dat[['is_oversegmented']]

    # Plotting
    def plot_imag_ad(self, ad, figsize=None, add_colorbar=True, bg_img=True,
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
        except:
            axs = [axs]
        object_name = ad.uns['ObjectName']
        for ax, (imid, dat) in zip(axs, ad.obs.groupby(['ImageId'])):
            mask = self.ioh.get_mask(imid, object_type=object_name)
            values = ad[dat.index, :].X.squeeze()
            labels = dat['ObjectNumber']
            img = plth.map_series_on_mask(mask, values, labels)

            colorbar = (ax == axs[-1]) and add_colorbar
            if bg_img:
                self.plot_bg_img(imid, ax=ax)
            plth.plot_heatmask(img, ax=ax, colorbar=colorbar, bad_alpha=bad_alpha, **kwargs)
            ax.axis('off')
        plth.adapt_ax_clims(axs)
        return axs

    def plot_bg_img(self, imgid, cmap=None, image_name='Mask2xBorderImg', ax=None):
        if ax is None:
            fig, ax = plt.subplots()
        if cmap is None:
            cmap = colors.ListedColormap(['black', 'darkgrey'])
        img = self.ioh.get_image(imgid, image_name).astype(float)

        ax.imshow(img, cmap=cmap,
                  interpolation='nearest', origin='lower')

    @classmethod
    def from_runname(cls, run, base_folder='..', comparison_folder='seg_comparison_v3',
                     image_categories=None):

        fn_labels = pathlib.Path(f'{base_folder}/{run}/{comparison_folder}/Label.csv')
        fn_labels_var = pathlib.Path(f'{base_folder}/{run}/{comparison_folder}/var_Label.csv')
        fn_imgs = pathlib.Path(f'{base_folder}/{run}/{comparison_folder}/Image.csv')
        fn_imgs_var = pathlib.Path(f'{base_folder}/{run}/{comparison_folder}/var_Image.csv')
        fol_images = pathlib.Path(f'{base_folder}/{run}/{comparison_folder}/imgs')
        fol_masks = pathlib.Path(f'{base_folder}/{run}/{comparison_folder}/masks')
        fn_maskimg = pathlib.Path(f'{base_folder}/{run}/{comparison_folder}/Mask2x.csv')
        fn_maskimg_var = pathlib.Path(f'{base_folder}/{run}/{comparison_folder}/var_Mask2x.csv')
        fn_object_relations = pathlib.Path(f'{base_folder}/{run}/{comparison_folder}/Object relationships.csv')
        segdata = cls(run, fn_imgs, fn_imgs_var)
        segdata.add_label_meas(fn_labels, fn_labels_var)
        segdata.add_cellmask_meas(fn_maskimg, fn_maskimg_var)
        segdata.add_iohelper(fol_images, fol_masks)
        if image_categories is not None:
            cpe.make_columns_categorical(segdata.ad_img.obs, image_categories)
        segdata.add_object_relations(fn_object_relations)
        segdata.add_percent_touching()
        return segdata
