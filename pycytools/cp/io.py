import functools

class IoHelper:
    """
    Helper class for lazy image and mask IO
    """

    def __init__(self, dat_img, fol_images, fol_masks):
        self.dat_img = dat_img
        self.fol_masks = fol_masks
        self.fol_images = fol_images

    @functools.lru_cache()
    def get_mask(self, imid, mask_name='cell'):
        img = self.dat_img.query(f'ImageId == "{imid}"')[f'FileName_{mask_name}'].iloc[0]
        return tifffile.imread(self.fol_masks / img)

    @functools.lru_cache()
    def get_image(self, imid, image_name='FullStackComp'):
        img = self.dat_img.query(f'ImageId == "{imid}"')[f'FileName_{image_name}'].iloc[0]
        return tifffile.imread(self.fol_images / img, out='memmap')

    def get_image_channel(self, imid, image_name='FullStackComp', channel_number=1):
        img = self.get_image(imid, image_name)
        if img.ndim == 2:
            assert channel_number == 1, ValueError("Plane_number needs to be 1 for single channel images")
            return img
        if img.shape[2] == self.dat_img.query(f'ImageId == {imid}')['image_shape_w'].iloc[0]:
            return img[channel_number - 1, :, :].squeeze()
        else:
            return img[:, :, channel_number - 1].squeeze()

