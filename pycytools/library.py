# -*- coding: utf-8 -*-
"""
Contains various functions for image processing 
@author: vitoz
"""

from __future__ import division

import json
import os

import numpy as np
import pandas as pd
import requests
import scipy as sp
import skimage as sk
import tifffile
import tifffile as tif
from scipy import ndimage as ndi
from skimage import filters
from skimage import measure
from skimage import morphology
from skimage import transform


def remove_outlier_pixels(img, threshold=50, mode='median'):
    mask = np.ones((3, 3))
    mask[1, 1] = 0
    img_median = filters.rank.median(img, mask)

    if mode == 'max':
        img_max = filters.rank.maximum(img, mask)
        imgfil = (img - img_max) > threshold
    elif mode == 'median':
        imgfil = (img - img_median) > threshold
    else:
        raise ('Mode must be: max or median')
    img_out = img.copy()
    img_out[imgfil] = img_median[imgfil]
    return img_out


def scale_images(img, cap_percentile=99, rescale=False):
    perc = np.percentile(img, cap_percentile)
    img[img > perc] = perc
    if rescale:
        img = sk.exposure.rescale_intensity(img)
    return img


def normalize_images(img, **kwargs):
    img = sk.exposure.equalize_hist(img, **kwargs)


def threshold_images(img, method='otsu',
                     thresh_cor=None,
                     thresh=None,
                     fill=False,
                     block_size=10,  # only for adaptive
                     **kwargs):
    if method.lower() == 'otsu':
        thresh = filters.threshold_otsu(img)

        if thresh_cor is None:
            tresh_img = img > thresh
        else:
            tresh_img = img > thresh * thresh_cor

    elif method.lower() == 'adaptive':
        thresh = filters.threshold_adaptive(img,
                                            block_size, **kwargs)
        if thresh_cor is None:
            tresh_img = img > thresh
        else:
            tresh_img = img > thresh * thresh_cor

    elif method.lower() == 'manual':
        if thresh is None:
            raise NameError(
                'when using manual thresholding, supply a threshold')

    else:
        raise NameError('Invalid threshold method used')

    if fill:
        tresh_img = sp.ndimage.binary_fill_holes(tresh_img)

    return tresh_img


def keep_max_area(tresh_img):
    lab = sk.measure.label(tresh_img)
    labMax = np.bincount(lab[lab > 0]).argmax()
    tresh_img_max = lab == labMax
    return tresh_img_max


def flip_img(img, axis):
    if axis == 1:
        img = np.fliplr(img)
    elif axis == 0:
        img = np.flipud(img)
    else:
        raise NameError('Axis: 0: up down, 1:left right')


def crop_img_to_binary(img, tresh_img):
    region = sk.measure.regionprops(tresh_img)
    minr, minc, maxr, maxc = region[0].bbox

    tresh_img = tresh_img[minr:maxr, minc:maxc]
    img = img[minr:maxr, minc:maxc]
    return (img, tresh_img)


def stretch_imgs_equal(img_list,
                       stretch_dim='w',  # w: widht, h: height, b: both
                       direction='min',  # min or max
                       interpol=None  # which interpolation algorithm
                       ):
    heights = np.array([float(img.shape[0]) for img in img_list])
    widths = np.array([float(img.shape[1]) for img in img_list])

    if direction == 'min':
        w_ref = widths.min()
        h_ref = heights.min()

    elif direction == 'max':
        w_ref = widths.max()
        h_ref = heights.max()

    if stretch_dim == 'w':
        w_scale = widths / float(w_ref)
        h_scale = w_scale

    if stretch_dim == 'h':
        h_scale = heights / float(h_ref)
        w_scale = h_scale

    if stretch_dim == 'b':
        h_scale = heights / float(h_ref)
        w_scale = widths / float(w_ref)

    widths = np.floor(widths / w_scale)
    heights = np.floor(heights / h_scale)
    # stretch everything to max widht/maxheight
    out_imgs = list()
    for (img, w, h) in zip(img_list, widths, heights):
        # do the rescaling
        img = sk.transform.resize(img, (h, w))
        out_imgs.append(img)
    return out_imgs


def blur_img_gauss(img, sigma=1, idKeys=None):
    blur_img = filters.gaussian_filter(img, sigma=sigma)
    return blur_img


def l2l_corr(img, dim=0):
    '''Calculates the line to line correlations between all lines of an image,
    represented as a 2D matrix img'''
    if dim == 0:
        img = img.T

    nCol = img.shape[1]
    corrArray = np.zeros(nCol - 1)

    for i in range(nCol - 1):
        corrArray[i] = np.corrcoef(img[:, i], img[:, i + 1])[1, 0]
    return (corrArray)


### tools for dealing with segmentation masks


def query_clone_infos_airlab(ids):
    """
    Use rauls API to query clone info from clone ids
    :param ids:
    :return: dict with the response
    """

    resp_dict = dict()
    for id in ids:
        resp = requests.get('http://airlaboratory.ch/apiLabPad/api/getInfoForClone/' + str(id))
        resp_entry = json.loads(resp.text)
        if (resp_entry != '0') & (len(resp_entry) > 0):
            resp_dict[id] = resp_entry[0]

    return resp_dict


def query_clone_names_airlab(ids, name_fields=['proName', "cloBindingRegion"], sep=' - '):
    """
    Queryis Rauls API for the clone name
    :param ids:
    :return:
    """
    resp_dict = query_clone_infos_airlab(ids)

    out_names = list()
    for id in ids:
        entry = resp_dict.get(id)

        try:
            outlist = [entry[n] for n in name_fields]
            name = sep.join(outlist)
            out_names.append(name)
        except:
            out_names.append(None)

    return out_names


def get_id_from_name(name):
    """
    Retreives an id from an airlab name
    :param name:
    :return:
    """

    newname = name.split('_')[-1]
    newname = newname.split('(')[0]

    if newname == '':
        newname = name

    return newname


def get_id_from_airlabname(name):
    """
    Directly get the clonenames from raulnames
    :param name:
    :return:
    """

    newname = name.split('_')[-1]
    newname = newname.split('(')[0]

    if newname == '':
        newname = name

    return newname


def get_names_from_airlabnames(names):
    """
    Tries to query a nice airlab name based on the id in the name.
    If query not successfull the old name is returned.
    :param names:
    :return:
    """
    ids = [get_id_from_airlabname(n) for n in names]

    al_names = query_clone_names_airlab(ids)

    namedict = {name: al_name for name, al_name in zip(names, al_names) if al_name is not None}

    newnames = [namedict.get(n, n) for n in names]

    return newnames


## working with masks

def find_touching_pixels(label_img, distance=1, selem=None):
    """
    Returns a mask indicating touching regions. Either provide a diameter for a disk shape
    distance or a selem mask.
    :param label_img: a label image with integer labels
    :param distance: =1: touching pixels, >1 pixels labels distance appart
    :param selem: optional, a selection mask, e.g. skimage.morphology.disk(1) (if this is bigger than
                    1 the 'distance' is not true.
    :return: a mask of the regions touching or are close up to a certain diameter
    """

    if selem is None:
        selem = morphology.disk(1)

    touch_mask = np.zeros(label_img.shape)
    not_bg = label_img > 0

    for i in np.unique(label_img):
        if i != 0:
            cur_lab = (label_img == i)
            # touch_mask[ndi.filters.maximum_filter(cur_lab,  footprint=selem) &
            #           not_bg & (cur_lab == False)] = 1

            touch_mask[ndi.binary_dilation(cur_lab, structure=selem, iterations=distance, mask=not_bg) &
                       (cur_lab == False)] = 1

    return touch_mask


def scale_labelmask(labelmask, scale):
    # assert (scaling % 1) == 0, "only integer scaling supported!"

    # rescale
    trans_labs = transform.rescale(labelmask + 1, scale=scale, preserve_range=True)

    trans_labs[(trans_labs % 1) > 0] = 1
    trans_labs = np.round(trans_labs) - 1
    #
    tmplabels = ndi.uniform_filter(trans_labs, size=2)
    trans_labs[trans_labs != tmplabels] = 0

    return trans_labs.astype(np.int)


def extract_mean_markers_by_mask(label_image, img_stack):
    label_image = np.squeeze(label_image)
    label_dict = dict()
    objects = ndi.find_objects(label_image)

    for i, sl in enumerate(objects):
        if sl is None:
            continue

        label = i + 1
        mask = label_image[sl] == label
        if np.any(mask):
            label_dict[label] = np.array([np.mean(slice[sl][mask]) for slice in img_stack])

    return label_dict


def apply_functions_to_labels(label_image, img_stack, fkt_list, out_array=None):
    """

    :param label_img:
    :param img_stack:
    :param fkt_dict: dict key: fkt_name, value: function of the form fkt(mask, img)
    :return:
    """

    label_image = np.squeeze(label_image)
    objects = ndi.find_objects(label_image)

    objects = [(i + 1, sl) for i, sl in enumerate(objects) if sl is not None]
    nobj = len(objects)
    nchannels = img_stack.shape[2]
    out_shape = (nobj * nchannels, len(fkt_list) + 1)
    if out_array is None:
        out_array = np.empty(out_shape)
    else:
        assert out_array.shape == out_shape, (out_array.shape, out_shape)

    for i, (label, sl) in enumerate(objects):
        out_idx = np.s_[(i * nchannels):((i + 1) * nchannels)]

        img_sl = img_stack[sl]
        print(img_stack.shape, label_image.shape)
        mask = label_image[sl] == label
        sl_image = [img_sl[..., i] for i in range(img_sl.shape[2])]
        t_out_array = out_array[out_idx]
        x = np.array([[fkt(mask, img) for fkt in fkt_list] for img in sl_image])
        t_out_array[:, 1:] = x
        t_out_array[:, 0] = label

    return out_array


def apply_functions_to_list_of_labels(label_image_list, img_stack_list, fkt_list, out_array=None):
    """

    :param ids:
    :param label_image_list:
    :param img_stack:
    :param fkt_list:
    :param out_array:
    :return:
    """

    nobjs = [len(np.unique(labs)) - 1 for labs in label_image_list]
    nchannels = img_stack_list[0].shape[2]
    nfkts = len(fkt_list)

    out_shape = (np.sum(nobjs) * nchannels, nfkts + 2)

    if out_array is None:
        out_array = np.empty(out_shape)
    else:
        assert (out_array.shape == out_shape)

    last_idx = 0
    for i, (labs, img_stack) in enumerate(zip(label_image_list, img_stack_list)):
        next_idx = (last_idx + nobjs[i] * nchannels)
        out_idx = np.s_[(last_idx):next_idx]
        t_out_array = out_array[out_idx, :]
        t_out_array[:, 0] = i
        apply_functions_to_labels(labs, img_stack, fkt_list, out_array=t_out_array[:, 1:])
        last_idx = next_idx

    return out_array


def apply_functions_to_list_of_labels_table(label_image_list,
                                            img_stack_list, fkt_list, fkt_names,
                                            channel_names, slice_ids=None):
    """

    :param label_image_list:
    :param img_stack_list:
    :param fkt_list:
    :param fkt_names:
    :param channel_names:
    :return:
    """
    dat = apply_functions_to_list_of_labels(label_image_list, img_stack_list, fkt_list)
    dat = pd.DataFrame(dat, columns=['cut_id', 'cell_id'] + list(fkt_names))
    dat['channel'] = np.tile(np.array(channel_names), dat.shape[0] / len(channel_names))

    if slice_ids is not None:
        slice_ids = np.array(slice_ids)
        dat['cut_id'] = slice_ids[dat['cut_id']]
    dat = dat.set_index(['cut_id', 'cell_id', 'channel'])
    dat = dat.unstack(level='channel')
    dat.columns.names = ['stat', 'channel']
    return dat


def extend_slice_touple(slice_touple, extent, max_dim, min_dim=(0, 0)):
    """
    Extends a numpy slice touple, e.g. corresponding to a bounding box
    :param slice_touple: a numpy slice
    :param extent: amount of extension in pixels
    :param max_dim: maximum image coordinates (e.g. from img.shape)
    :param min_dim: minimum image coordinates, usually (0,0)
    :return: an extended numpy slice

    """

    new_slice = tuple(_extend_slice(s, extent, d_max, d_min) for s, d_max, d_min in
                      zip(slice_touple, max_dim, min_dim))

    return new_slice


def _extend_slice(sl, extent, dim_max, dim_min=0):
    """
    helper function to extend single slices
    :param sl: numpy slice
    :param extent: how many pixels should be extended
    :param dim_max: maximum coordinate in dimension
    :param dim_min: minimum coordinate in dimension, e.g. 0
    :return: the new extended slice
    """

    x_start = max(sl.start - extent, dim_min)
    x_end = min(sl.stop + extent, dim_max)

    return np.s_[x_start:x_end]


def add_slice_dimension(sl, append=True):
    """
    Appends another dimension to a numpy slice
    :param sl: a numpy slice
    :return: a numpy slice extended for 1 dimension


    """

    if append:
        exsl = tuple([s for s in sl] + [np.s_[:]])
    else:
        exsl = tuple([np.s_[:]] + [s for s in sl])
    return exsl


def map_series_on_mask(mask, series, label=None):
    """
    TODO: A good docstring here
    :param mask:
    :param series:
    :param label:
    :return:
    """
    if label is None:
        label = series.index

    # make a dict

    labeldict = np.empty(mask.max() + 1)
    labeldict[:] = np.NaN

    for lab, val in zip(label, series):
        labeldict[int(lab)] = val

    out_img = labeldict[mask.flatten()]
    out_img = np.reshape(out_img, mask.shape)
    out_img = np.ma.array(out_img, mask=mask == 0)
    return out_img


def create_neightbourhood_dict(label_mask, bg_label=0):
    """
    Creates a dictionary indicating neightbourhood of cells

    :param label_mask:
    :return: nb_dict: a with key=label and entry=neightbour label
    """

    vertices, edges = make_neighbourhood_graph(label_mask)
    nb_dict = dict((v, list()) for v in vertices if v != bg_label)

    for e in edges:
        if (e[0] != bg_label) & (e[0] != bg_label):
            nb_dict[e[0]].append(e[1])
            nb_dict[e[1]].append(e[0])

    return nb_dict


def make_neighbourhood_graph(label_mask, uni_edges=True):
    """
    Adapted from the internet


    :param label_mask:
    :return: vertices, edges: vertices and edges of the neighbourhood graph, includes  background labels
    """
    # get unique labels
    grid = label_mask
    vertices = np.unique(grid)

    # map unique labels to [1,...,num_labels]
    # -> otherwise the hashing will not work
    reverse_dict = dict(zip(vertices, np.arange(len(vertices))))
    grid = np.array([reverse_dict[x] for x in grid.flat]).reshape(grid.shape)

    # create edges
    down = np.c_[grid[:-1, :].ravel(), grid[1:, :].ravel()]
    right = np.c_[grid[:, :-1].ravel(), grid[:, 1:].ravel()]
    all_edges = np.vstack([right, down])
    all_edges = all_edges[all_edges[:, 0] != all_edges[:, 1], :]
    all_edges = np.sort(all_edges, axis=1)
    num_vertices = len(vertices)
    edge_hash = all_edges[:, 0] + num_vertices * all_edges[:, 1]
    # find unique connections
    edges = np.unique(edge_hash)
    # undo hashing
    edges = [[vertices[x % num_vertices],
              vertices[x / num_vertices]] for x in edges]

    return vertices, edges


def save_object_stack(folder, basename, img_stack, slices):
    """
    Saves slices from an image stack as.
    :param folder: The folder to save it in
    :param basename: The filename
    :param img_stack: the image stack. should be CXY
    :param slices: a list of numpy slices sphecifying the regions to be saved
    :return:
    """

    for lab, sl in enumerate(slices):
        if sl is None:
            pass
        x = sl[0].start
        y = sl[1].start

        exsl = add_slice_dimension(sl, append=False)

        fn = os.path.join(folder, basename + '_l' + str(lab + 1) + '_x' + str(x) + '_y' + str(y) + '.tiff')

        with tifffile.TiffWriter(fn, imagej=True) as tif:
            timg = img_stack[exsl]

            for chan in range(timg.shape[0]):
                tif.save(timg[chan, :, :].squeeze())


## for processing cellprofiler output
def name_from_metal(metal, namedict, sep=None):
    """
    Returns a funciton 'beautify names' that generates names
    according to: beautify_names(oldname) -> newname_oldname
    :param namedict:
    :return:
    """
    if sep is None:
        sep = '_'
    newname = sep.join([namedict.get(metal, metal), metal])
    return newname


def metal_from_name(name, sep=None):
    """

    :param name:
    :return:
    """

    if sep is None:
        sep = '_'
    return name.split(sep)[-1]


def add_masks_to_imgdata(dat_image, mask_fncol, base_folder, re_meta):
    """
    adds the mask data to the image data
    :param dat_image: a pandas frame from the loaded cellprofiler metadata
    :param mask_fncol: the column containing the mask filenames
    :param base_folder: the folder where the data resides
    :param re_meta: a regexp parsing mask metadata from the mask filenames.
            needs at least to contain a field 'site' giving the site name
            optional fields are:
                x, y: position of the topleft corner of the acquisition site
                cutid: id of the cut=the subregion of the current site

    :return: dat_image: the modified dat_image
    """

    dat_image['mask'] = dat_image[mask_fncol].map(
        lambda fn: tif.imread(os.path.join(base_folder, fn)))

    groupdicts = dat_image[mask_fncol].map(lambda x: re_meta.search(x).groupdict())
    if ('x' in groupdicts[0]) & ('y' in groupdicts[0]):
        dat_image['x'] = [int(g['x']) for g in groupdicts]
        dat_image['y'] = [int(g['y']) for g in groupdicts]
    else:
        dat_image['x'] = 0
        dat_image['y'] = 0
    if 'cutid' in groupdicts[0]:
        dat_image['cutid'] = [g['cutid'] for g in groupdicts]
    dat_image['site'] = [g['site'] for g in groupdicts]

    dat_image['h'], dat_image['w'] = zip(*dat_image['mask'].map(lambda x: x.shape))
    dat_image['slice'] = dat_image.apply(lambda x: [(np.s_[x['x']:(x['x'] + x['h'])], np.s_[x['y']:(x['y'] + x['w'])])],
                                         axis=1)
    dat_image['slice'] = dat_image['slice'].map(lambda x: x[0])
    return dat_image


# varia
def get_real_dist2rim(x_dist, radius_cut, radius_sphere):
    """
    Get the real distance to rim
    :param x_dist:
    :param radius_cut:
    :param radius_sphere:
    :return:
    """
    x_transf = x_dist * ((radius_sphere) - np.sqrt((radius_sphere) ** 2 - (radius_cut) ** 2)) / radius_cut
    return x_transf


def aggregate_nb_data(cell_dat, nb_dict, fil=None, agg_fkt=np.mean, out_array=None):
    """
    """
    if fil is None:
        fil_idx = []
    else:
        fil_idx = cell_dat.index[fil == False]

    if out_array is not None:
        nb_dat = out_array
    else:
        out_dat = cell_dat.copy()
        out_dat.loc[:] = np.nan
        nb_dat = out_dat.values

    id_dict = {cellid: int(idx) for idx, cellid in enumerate(cell_dat.index) if cellid not in fil_idx}
    dat_idx = id_dict.keys()

    for cid, nids in nb_dict.items():
        if (nids != []) & (cid in dat_idx) & all(i in dat_idx for i in nids):
            nidxs = np.array([id_dict[i] for i in nids if i != cid])
            if nidxs != []:
                nb_dat[id_dict[cid], :] = np.apply_along_axis(agg_fkt, 0, cell_dat.values[nidxs, :])

    if out_array is not None:
        return True
    else:
        return out_dat


def aggregate_nb_data_imgs(cell_dat_img, nb_dicts, value_col='cell_int_mean', agg_fkt=np.mean, fil_col=None,
                           out_value_col='cell_nb_mean', imgid_level='cut_id', cellid_level='cell_id'):
    """
    Aggregates data based on neighbouhood dicts
    """

    assert (len(cell_dat_img.index.names) == 2)

    if cell_dat_img.index.names[0] != imgid_level:
        cell_dat_img = cell_dat_img.swaplevel(0, 1, axis=0)

    out_dats = cell_dat_img[value_col].copy()
    out_dats.loc[:] = np.nan

    for imgid in nb_dicts.index.get_level_values(imgid_level).unique():

        cell_dat = cell_dat_img.xs(imgid, level=imgid_level)

        if len(nb_dicts.index.names) == 1:
            nb_dict = nb_dicts.xs(imgid)
        else:
            nb_dict = nb_dicts.xs(imgid, level=imgid_level)[0]

        if fil_col is not None:
            fil = cell_dat.loc[:, fil_col] == True
        else:
            fil = None

        in_cell_dat = cell_dat.loc[:, value_col]
        aggregate_nb_data(cell_dat=in_cell_dat, nb_dict=nb_dict, fil=fil, agg_fkt=agg_fkt,
                          out_array=out_dats.loc[imgid].values)

    out_dats = pd.concat({out_value_col: out_dats}, axis=1, names=cell_dat_img.columns.names)
    return out_dats


def get_nb_dict(coldat):
    """
    Converts relationship lists to dict
    """
    first_obj = coldat.iloc[:, 0]
    second_obj = coldat.iloc[:, 1]

    nb_dict = dict((obj, set()) for obj in np.unique(first_obj))

    for f, s in zip(first_obj, second_obj):
        nb_dict[f].add(s)

    return nb_dict
