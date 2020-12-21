import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage.filters import gaussian_filter

import pycytools.library as lib


def plot_rgb_imc(imc_img, metals, norm_perc=99.9, sigma=1, outlierthresh=30, saturation=1):
    plt.figure()
    imgstack = [imc_img.get_img_by_metal(m) for m in metals]
    imgstack = _preproc_img_stack(imgstack, norm_perc, sigma, outlierthresh)
    pimg = np.stack(imgstack, axis=2)
    pimg = pimg * saturation
    pimg[pimg > 1] = 1
    plt.imshow(pimg, interpolation='nearest')
    plt.axis('off')


def plot_rgbw_imc(imc_img, metals, w_metal, white_weight=0.4, norm_perc=99.9, sigma=1, outlierthresh=30):
    plt.figure()
    imgstack = [imc_img.get_img_by_metal(m) for m in metals + [w_metal]]
    imgstack = _preproc_img_stack(imgstack, norm_perc, sigma, outlierthresh)
    pimg = np.stack(imgstack[:3], axis=2) + np.repeat(np.expand_dims(imgstack[3], 2) * white_weight, 3, 2)
    pimg[pimg > 1] = 1
    plt.imshow(pimg, interpolation='nearest')
    plt.axis('off')


def _preproc_img_stack(imgstack, norm_perc=99.9, sigma=1, outlierthresh=30):
    imgstack = [lib.remove_outlier_pixels(im.astype(np.uint16), threshold=outlierthresh) for im in imgstack]
    imgstack = [gaussian_filter(im, sigma=sigma) for im in imgstack]
    imgstack = [im.astype(np.float) / np.percentile(im, norm_perc) for im in imgstack]
    for im in imgstack:
        im[im > 1] = 1
    return imgstack


def get_7_color_img(imc_img, metals, norm_perc=99.9, alphas=None, sigma=1, outlierthresh=30, saturation=1):
    """
    Color.red,Color.green,Color.blue,
    Color.white,Color.cyan,Color.magenta,Color.yellow
    """
    cols = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 1), (0, 1, 1), (1, 0, 1), (1, 1, 0)]
    imgstack = [imc_img.get_img_by_metal(m) for m in metals if m != 0]
    curcols = [c for m, c in zip(metals, cols) if m != 0]
    imgstack = _preproc_img_stack(imgstack, norm_perc, sigma, outlierthresh)

    if alphas is None:
        alphas = np.repeat(1 / len(imgstack), len(imgstack))
    else:
        alphas = [a for m, a in zip(metals, alphas) if m != 0]
    imgstack = [np.stack([im * c * a for c in col], axis=2) for im, col, a in zip(imgstack, curcols, alphas)]

    pimg = np.sum(imgstack, axis=0)
    pimg = pimg * saturation
    pimg[pimg > 1] = 1

    return pimg.squeeze()


def plot_7_color_img(imc_img, metals, norm_perc=99.9, alphas=None, sigma=1, outlierthresh=30, saturation=1):
    plt.figure()
    pimg = get_7_color_img(imc_img, metals, norm_perc, alphas, sigma, outlierthresh, saturation)
    plt.imshow(pimg.squeeze(), interpolation='nearest')
    plt.axis('off')

def plot_mask_contour(mask, ax=None, linewidths=0.5, linestyles=':', color='Gray', alpha=1):
    """
    Adds background mask contour
    """
    if ax is None:
        fig = plt.figure(figsize=(20, 20))
        ax = plt.gca()
    ax.contour(mask, [0, 0.5], colors=[color], linewidths=linewidths, linestyles=linestyles, alpha=alpha)
    return ax

def plot_heatmask(img, *, cmap=None, cmap_mask=None, cmap_mask_alpha=0.3, colorbar=True, ax=None,
                  bad_color='k', bad_alpha=1, crange=None, norm=None):
    """
    Plots an image with nice defaults for masked pixels.
    """
    if cmap is None:
        cmap = plt.cm.viridis
    cmap = copy.copy(cmap)
    cmap.set_bad(bad_color, bad_alpha)
    if ax is None:
        plt.close()
        fig, ax = plt.subplots(1, 1)
    else:
        fig = ax.get_figure()

    cax = ax.imshow(img, cmap=cmap, interpolation="nearest", norm=norm)
    if colorbar:
        fig.colorbar(cax)

    if crange is not None:
        cax.set_clim(crange[0], crange[1])

    if hasattr(img, "mask"):
        mask_img = np.isnan(img)
        if np.any(mask_img):
            mask_img = np.ma.array(mask_img, mask=img.mask | (mask_img == False))
            if cmap_mask is None:
                cmap_mask = "Greys"
            ax.imshow(
                mask_img == 1,
                cmap=cmap_mask,
                alpha=cmap_mask_alpha,
                interpolation="nearest",
            )
    ax.axis('off')
    return ax

def add_scalebar(
        ax, resolution=0.000001, location=4, color="white", pad=0.5, frameon=False, **kwargs
):
    """
    Adds a scalebar
    """
    scalebar = ScaleBar(
        resolution, location=location, color=color, pad=pad, frameon=frameon, **kwargs
    )  # 1 pixel = 0.2 meter
    ax.add_artist(scalebar)

def adapt_ax_clims(axs, imgnr=0):
    """
    Adapts color axes limits such that they are shared by the all images
    """
    caxs = [ax.images[imgnr] for ax in axs if len(ax.images) > 0]
    clims = [cax.get_clim() for cax in caxs]
    clims = [c for c in clims if c != (True, True)]
    clim_all = [f(c) for f, c in zip([np.min, np.max], zip(*clims))]
    for cax in caxs:
        cax.set_clim(clim_all)