import pycytools as pct
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import ipywidgets as ipw
import functools as ft
import pycytools.library as lib
import skimage as ski


def plot_rgb_imc(imc_img, metals, norm_perc=99.9, sigma=1, outlierthresh=30, saturation=1):
    plt.figure()
    imgstack = [imc_img.get_img_by_metal(m) for m in metals]
    imgstack = _preproc_img_stack(imgstack, norm_perc, sigma, outlierthresh)
    pimg = np.stack(imgstack, axis=2)
    pimg = pimg*saturation
    pimg[pimg > 1] =1
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
    imgstack = [ski.filters.gaussian_filter(im, sigma=sigma) for im in imgstack]
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
    pimg = pimg*saturation
    pimg[pimg > 1] = 1

    return pimg.squeeze()


def plot_7_color_img(imc_img, metals, norm_perc=99.9, alphas=None, sigma=1, outlierthresh=30, saturation=1):
    plt.figure()
    pimg = get_7_color_img(imc_img, metals, norm_perc, alphas, sigma, outlierthresh, saturation)
    plt.imshow(pimg.squeeze(), interpolation='nearest')
    plt.axis('off')






    # def ipw_marker_vs_marker(pdat, transf_dict, name_dict, col_level1='measure', col_level2='mass', cut_level='ImageNumber')
#     stat = pdat.columns.get_level_values(col_level1)
#     marker = pdat.columns.get_level_values(col_level2)
#
#
#     #w = ipw.interactive(ft.partial(transf_dict=transf_dict),
#     #                    _ipw_marker_vs_marker,
#                         (pdat,stat1, m1,transform1, stat2, m2, transform2, fit, color_cut, fixed(transf_dict),)

# def _ipw_marker_vs_marker(pdat,stat1, m1,transform1, stat2, m2, transform2, fit, color_cut, transf_dict, name_dict):
#     dat1 = pdat[stat1]
#     dat2 = pdat[stat2]
#     m1 = pct.library.metal_from_name(m1)
#     m2 = pct.library.metal_from_name(m2)
#     x = dat1[m1]
#     y = dat2[m2]
#
#     nafil = np.isfinite(x) & np.isfinite(y)
#     x = x[nafil]
#     y = y[nafil]
#
#     transfkt = transf_dict[transform]
#     x = np.array(transfkt(x))
#     y = np.array(transfkt(y))
#
#
# def marker_vs_marker(x, y, fit,):
#
#     plt.close()
#     g = sns.jointplot(x, y, alpha=0.5)
#     if color_cut:
#         r = np.arange(len(x))
#         np.random.shuffle(r)
#         c = pdat.index.get_level_values(level='ImageNumber')[nafil][r]
#
#         col_pal = sns.color_palette("hls",max(c)+1)
#         cols = [col_pal[int(i)] for i in c]
#         g.ax_joint.scatter(x[r],y[r], color=cols)
#
#     g.set_axis_labels(stat1+' '+ m1, stat2+' '+m2)
#
#     #g.title(np.corrcoef(x,y)[1,0])
#
#     if fit:
#         lm_mod = lm.LinearRegression(fit_intercept=True)
#         mod = lm.RANSACRegressor(lm_mod)
#         mod.fit(x.reshape(-1, 1),y)
#         y_pred = mod.predict(x.reshape(-1, 1))
#         g.ax_joint.plot(x,y_pred, color='r')
#
#         plt.title('Pearson: {:.2}\n Spearman: {:.2}\nSlope: {:.2}\nIntercept: {:.2}\n'.format(
#                 np.corrcoef(x,y)[1,0],scistats.spearmanr(x, y)[0],
#                 mod.estimator_.coef_[0], mod.estimator_.intercept_))
#     #else:
#         #plt.title('Corcoef: {:.2}'.format(np.corrcoef(x,y)[1,0]))
