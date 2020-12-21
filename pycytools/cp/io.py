import functools
from pycytools.cp.vars import COL_DATATYPE, COL_COLUMN_NAME, IS_FLOAT, IMAGE_ID, IMAGE_NUMBER, OBJECT_ID, OBJECT_NUMBER, \
    OBJECT_MASK_NAME, RUN, COL_SCALING, FEATURE_NAME, IMAGE_NAME, OBJECT_NAME, CHANNEL
class IoHelper:
    """
    Helper class for lazy image and mask IO
    """

    def __init__(self, dat_img, fol_images, fol_masks, default_image=None,
                 default_mask=None):
        self.dat_img = dat_img
        self.fol_masks = fol_masks
        self.fol_images = fol_images
        self.default_mask = default_mask
        self.default_image = default_image

    @functools.lru_cache()
    def get_mask(self, imid, mask_name=None):
        if mask_name is None:
            mask_name = self.default_mask
        img = self.dat_img.query(f'ImageId == "{imid}"')[f'FileName_{mask_name}'].iloc[0]
        return tifffile.imread(self.fol_masks / img)

    @functools.lru_cache()
    def get_image(self, imid, image_name=None):
        if image_name is None:
            image_name=self.default_image
        img = self.dat_img.query(f'{IMAGE_ID}== "{imid}"')[f'FileName_{image_name}'].iloc[0]
        return tifffile.imread(self.fol_images / img, out='memmap')

    def get_image_channel(self, imid, image_name=None, channel_number=1):
        img = self.get_image(imid, image_name)
        if img.ndim == 2:
            assert channel_number == 1, ValueError("Plane_number needs to be 1 for single channel images")
            return img
        if img.shape[2] == self.dat_img.query(f'ImageId == {imid}')['image_shape_w'].iloc[0]:
            return img[channel_number - 1, :, :].squeeze()
        else:
            return img[:, :, channel_number - 1].squeeze()

