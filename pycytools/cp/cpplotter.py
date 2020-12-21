import matplotlib.pyplot as plt

import pycytools.library as lib
import pycytools.plots as plth
from pycytools.cp.vars import IMAGE_ID, OBJECT_NUMBER, \
    OBJECT_MASK_NAME


class CpPlotter:
    def __init__(self, cp_experiment):
        self.cpe = cp_experiment

    def plot_ad_heatmask(self, ad, figsize=None, add_colorbar=True, add_scalebar=True,
                         bad_alpha=1, ax=None, boundaries=True, boundaries_kwargs=None,
                         scalebar_kwargs=None,
                         **kwargs):
        """
        Plots maps the values contained in the anndata var on the object masks,
        plotting the individual images as columns.

        :param ad: an anndata with obs variables: 'image_id', 'object_type', 'object_number'.
                    The anndata needst to be filtered to contain only 1 var - the value to be maped on the mask.
        :param figsize: the output image size
        :param add_colorbar: should a colorbar be added?
        :param add_scalebar: should a scalebar be added?
        :param bad_alpha: Should the background be black (=1) or transparent (=1)
        :param ax: axis to plot on
        :param boundaries: should cell boundaries be plotted?
        :param boundaries_kwargs: Additional parameters to style cell boundaries
        :param scalebar_kwargs: Additional parameters to style the scalebar
        :param kwargs: Additional parameters for 'plot_heatmask'

        :returns: the figure axes
        """
        assert ad.X.shape[1] == 1, "Subset the anndata until it has at most 1 value"
        imgids = ad.obs[IMAGE_ID].unique()
        if ax is None:
            fig, axs = plt.subplots(ncols=len(imgids), figsize=figsize)
        else:
            assert len(imgids) == 0
            axs = [ax]
        try:
            len(axs)
        except TypeError:
            axs = [axs]
        object_mask_name = ad.uns[OBJECT_MASK_NAME]
        for ax, (imid, dat) in zip(axs, ad.obs.groupby([IMAGE_ID])):
            mask = self.cpe.ioh.get_mask(imid, mask_name=object_mask_name)
            values = ad[dat.index, :].X.squeeze()
            labels = dat[OBJECT_NUMBER]
            img = lib.map_series_on_mask(mask, values, labels)

            colorbar = (ax == axs[-1]) and add_colorbar
            plth.plot_heatmask(img, ax=ax, colorbar=colorbar, bad_alpha=bad_alpha, **kwargs)
            ax.axis('off')
            if boundaries:
                if boundaries_kwargs is None:
                    boundaries_kwargs = {}
                plth.plot_mask_boundaries(mask, ax=ax, **boundaries_kwargs)

            if add_scalebar:
                if scalebar_kwargs is None:
                    scalebar_kwargs = {}
                plth.add_scalebar(ax, **scalebar_kwargs)
        plth.adapt_ax_clims(axs)
        return axs

    def plot_sc_image(self, imid, image_name, channel_number, ax=None, object_boundaries=None,
                      boundaries_kwargs=None, add_colorbar=True, add_scalebar=True,
                      scalebar_kwargs=None, **kwargs):
        """
        Plot singgle channel image
        :params imid: image id of image scene to plot
        :params image_name: Name of the image stack to plot
        :params channel_number: Channel number to plot
        :params ax: plot axis
        :params object_boundaries: None or name of object boundaries to plot over the image
        :params boundaries_kwargs: Kwargs for plotting the boundaries
        :params add_colorbar: add a colorbar?
        :params add_scalebar: add a scalebar?
        :params scalebar_kwargs: kwargs for scalebar
        :params: **kwargs: kwargs passed to plot_heamask

        Returns:
            ax: the axis of the plot
        """
        img = self.cpe.ioh.get_image_channel(imid, image_name, int(channel_number))
        if ax is None:
            fig, ax = plt.subplots()
        plth.plot_heatmask(img, ax=ax, colorbar=add_colorbar, **kwargs)
        if object_boundaries is not None:
            maskname = self.cpe.get_mask_name(object_boundaries)
            mask = self.cpe.ioh.get_mask(imid, maskname)
            if boundaries_kwargs is None:
                boundaries_kwargs = {}
            plth.plot_mask_boundaries(mask, ax=ax, **boundaries_kwargs)
        if add_scalebar:
            if scalebar_kwargs is None:
                scalebar_kwargs = {}
            plth.add_scalebar(ax, **scalebar_kwargs)
        return ax
