import monai
import os
import numpy as np
from monai.transforms import (
    Compose,
    LoadImaged,
    Rotate90d,
    ScaleIntensityd,
    EnsureChannelFirstd,
    ResizeWithPadOrCropd,
    DivisiblePadd,
    ThresholdIntensityd,
    NormalizeIntensityd,
    SqueezeDimd,
    Identityd,
)

from monai.data import Dataset
from torch.utils.data import DataLoader
import torch

def get_file_list(data_pelvis_path, train_number, val_number):
    #list all files in the folder
    file_list=[i for i in os.listdir(data_pelvis_path) if 'overview' not in i]
    file_list_path=[os.path.join(data_pelvis_path,i) for i in file_list]
    #list all ct and mr files in folder
    ct_file_list=[os.path.join(j,'ct.nii.gz') for j in file_list_path]
    mr_file_list=[os.path.join(j,'mr.nii.gz') for j in file_list_path] #mr
    # Dict Version
    train_ds = [{'image': i, 'label': j, 'A_paths': i, 'B_paths': j} for i, j in zip(mr_file_list[0:train_number], ct_file_list[0:train_number])]
    val_ds = [{'image': i, 'label': j, 'A_paths': i, 'B_paths': j} for i, j in zip(mr_file_list[-val_number:], ct_file_list[-val_number:])]
    print('all files in dataset:',len(file_list))
    return train_ds, val_ds

##### slices #####
def load_volumes(train_transforms, train_ds, val_ds, saved_name_train=None, saved_name_val=None,ifsave=False,ifcheck=False):
    train_volume_ds = monai.data.Dataset(data=train_ds, transform=train_transforms) 
    val_volume_ds = monai.data.Dataset(data=val_ds, transform=train_transforms)
    if ifsave:
        save_volumes(train_ds, val_ds, saved_name_train, saved_name_val)
    if ifcheck:
        check_volumes(train_ds, train_volume_ds, val_volume_ds, val_ds)
    return train_volume_ds,val_volume_ds

def load_batch_slices(train_volume_ds,val_volume_ds, train_batch_size=5,val_batch_size=1,window_width=1,ifcheck=True):
    patch_func = monai.data.PatchIterd(
        keys=["image", "label"],
        patch_size=(None, None, window_width),  # dynamic first two dimensions
        start_pos=(0, 0, 0)
    )
    if window_width==1:
        patch_transform = Compose(
            [
                SqueezeDimd(keys=["image", "label"], dim=-1),  # squeeze the last dim
            ]
        )
    else:
        patch_transform = None
    # for training
    train_patch_ds = monai.data.GridPatchDataset(
        data=train_volume_ds, patch_iter=patch_func, transform=patch_transform, with_coordinates=False)
    train_loader = DataLoader(
        train_patch_ds,
        batch_size=train_batch_size,
        num_workers=2,
        pin_memory=torch.cuda.is_available(),
    )

    # for validation
    val_loader = DataLoader(
        val_volume_ds, 
        num_workers=1, 
        batch_size=val_batch_size,
        pin_memory=torch.cuda.is_available())
    
    if ifcheck:
        check_batch_data(train_loader,val_loader,train_patch_ds,val_volume_ds,train_batch_size,val_batch_size)
    return train_loader,val_loader

def load_batch_slices3D(train_volume_ds,val_volume_ds, train_batch_size=5,val_batch_size=1,ifcheck=True):
    patch_func = monai.data.PatchIterd(
        keys=["image", "label"],
        patch_size=(None, None,32),  # dynamic first two dimensions
        start_pos=(0, 0, 0)
    )

    # for training
    train_patch_ds = monai.data.GridPatchDataset(
        data=train_volume_ds, patch_iter=patch_func, with_coordinates=False)
    train_loader = DataLoader(
        train_patch_ds,
        batch_size=train_batch_size,
        num_workers=2,
        pin_memory=torch.cuda.is_available(),
    )

    # for validation
    val_loader = DataLoader(
        val_volume_ds, 
        num_workers=1, 
        batch_size=val_batch_size,
        pin_memory=torch.cuda.is_available())
    
    if ifcheck:
        check_batch_data(train_loader,val_loader,train_patch_ds,val_volume_ds,train_batch_size,val_batch_size)
    return train_loader,val_loader
    
def get_transforms(normalize,resized_size,div_size):
    transform_list=[]
    transform_list.append(LoadImaged(keys=["image", "label"]))
    transform_list.append(EnsureChannelFirstd(keys=["image", "label"]))

    if normalize=='zscore':
        transform_list.append(NormalizeIntensityd(keys=["image", "label"], nonzero=False, channel_wise=True))
        print('zscore normalization')

    elif normalize=='minmax':
        transform_list.append(ScaleIntensityd(keys=["image", "label"], minv=-1.0, maxv=1.0))
        print('minmax normalization')
    elif normalize=='none':
        print('no normalization')

    transform_list.append(ResizeWithPadOrCropd(keys=["image", "label"], spatial_size=resized_size,mode="minimum"))
    transform_list.append(Rotate90d(keys=["image", "label"], k=3))
    transform_list.append(DivisiblePadd(["image", "label"], k=div_size, mode="minimum"))
    train_transforms = Compose(transform_list)
    # volume-level transforms for both image and label
    return train_transforms

def myslicesloader(data_pelvis_path,
                   normalize='zscore',
                   train_number=1,
                   val_number=1,
                   train_batch_size=8,
                   val_batch_size=1,
                   saved_name_train='./train_ds_2d.csv',
                   saved_name_val='./val_ds_2d.csv',
                   resized_size=(600,400,None),
                   div_size=(16,16,None),
                   ifcheck_volume=True,
                   ifcheck_sclices=False,):
    
    # volume-level transforms for both image and label
    train_transforms = get_transforms(normalize,resized_size,div_size)
    train_ds, val_ds = get_file_list(data_pelvis_path, 
                                     train_number, 
                                     val_number)
    train_volume_ds, val_volume_ds = load_volumes(train_transforms, 
                                                train_ds, 
                                                val_ds, 
                                                saved_name_train, 
                                                saved_name_val,
                                                ifsave=False,
                                                ifcheck=ifcheck_volume)
    train_loader,val_loader = load_batch_slices(train_volume_ds, 
                                                val_volume_ds, 
                                                train_batch_size,
                                                val_batch_size=val_batch_size,
                                                window_width=1,
                                                ifcheck=ifcheck_sclices)
    return train_volume_ds,val_volume_ds,train_loader,val_loader,train_transforms

def mydataloader_3d(data_pelvis_path,
                   train_number,
                   val_number,
                   train_batch_size,
                   val_batch_size,
                   saved_name_train='./train_ds_2d.csv',
                   saved_name_val='./val_ds_2d.csv',
                   resized_size=(600,400,150),
                   div_size=(16,16,16),
                   ifcheck_volume=True,):
    # volume-level transforms for both image and segmentation
    normalize='zscore'
    train_transforms = get_transforms(normalize,resized_size,div_size)
    
    train_ds, val_ds = get_file_list(data_pelvis_path, 
                                     train_number, 
                                     val_number)
    #train_volume_ds, val_volume_ds 
    
    train_volume_ds,val_volume_ds = load_volumes(train_transforms=train_transforms, 
                                                train_ds=train_ds, 
                                                val_ds=val_ds, 
                                                saved_name_train=saved_name_train, 
                                                saved_name_val=saved_name_train,
                                                ifsave=True,
                                                ifcheck=ifcheck_volume)
    '''
    train_loader = DataLoader(train_volume_ds, batch_size=train_batch_size)
    val_loader = DataLoader(val_volume_ds, batch_size=val_batch_size)
    '''
    ifcheck_sclices=False
    train_loader,val_loader = load_batch_slices3D(train_volume_ds, 
                                                val_volume_ds, 
                                                train_batch_size,
                                                val_batch_size=val_batch_size,
                                                ifcheck=ifcheck_sclices)
                                                
    return train_loader,val_loader,train_transforms

def get_length(dataset, patch_batch_size):
    loader=DataLoader(dataset, batch_size=1)
    iterator = iter(loader)
    sum_nslices=0
    for idx in range(len(loader)):
        check_data = next(iterator)
        nslices=check_data['image'].shape[-1]
        sum_nslices+=nslices
    if sum_nslices%patch_batch_size==0:
        return sum_nslices//patch_batch_size
    else:
        return sum_nslices//patch_batch_size+1


def check_volumes(train_ds, train_volume_ds, val_volume_ds, val_ds):
    # use batch_size=1 to check the volumes because the input volumes have different shapes
    train_loader = DataLoader(train_volume_ds, batch_size=1)
    val_loader = DataLoader(val_volume_ds, batch_size=1)
    train_iterator = iter(train_loader)
    val_iterator = iter(val_loader)
    print('check training data:')
    idx=0
    for idx in range(len(train_loader)):
        try:
            train_check_data = next(train_iterator)
            ds_idx = idx * 1
            current_item = train_ds[ds_idx]
            current_name = os.path.basename(os.path.dirname(current_item['image']))
            print(idx, current_name, 'image:', train_check_data['image'].shape, 'label:', train_check_data['label'].shape)
        except:
            ds_idx = idx * 1
            current_item = train_ds[ds_idx]
            current_name = os.path.basename(os.path.dirname(current_item['image']))
            print('check data error! Check the input data:',current_name)
    print("checked all training data.")

    print('check validation data:')
    idx=0
    for idx in range(len(val_loader)):
        try:
            val_check_data = next(val_iterator)
            ds_idx = idx * 1
            current_item = val_ds[ds_idx]
            current_name = os.path.basename(os.path.dirname(current_item['image']))
            print(idx, current_name, 'image:', val_check_data['image'].shape, 'label:', val_check_data['label'].shape)
        except:
            ds_idx = idx * 1
            current_item = val_ds[ds_idx]
            current_name = os.path.basename(os.path.dirname(current_item['image']))
            print('check data error! Check the input data:',current_name)
    print("checked all validation data.")

def save_volumes(train_ds, val_ds, saved_name_train, saved_name_val):
    shape_list_train=[]
    shape_list_val=[]
    # use the function of saving information before
    for sample in train_ds:
        name = os.path.basename(os.path.dirname(sample['image']))
        shape_list_train.append({'patient': name})
    for sample in val_ds:
        name = os.path.basename(os.path.dirname(sample['image']))
        shape_list_val.append({'patient': name})
    np.savetxt(saved_name_train,shape_list_train,delimiter=',',fmt='%s',newline='\n') # f means format, r means raw string
    np.savetxt(saved_name_val,shape_list_val,delimiter=',',fmt='%s',newline='\n') # f means format, r means raw string


def check_batch_data(train_loader,val_loader,train_patch_ds,val_volume_ds,train_batch_size,val_batch_size):
    for idx, train_check_data in enumerate(train_loader):
        ds_idx = idx * train_batch_size
        current_item = train_patch_ds[ds_idx]
        print('check train data:')
        print(current_item, 'image:', train_check_data['image'].shape, 'label:', train_check_data['label'].shape)
    
    for idx, val_check_data in enumerate(val_loader):
        ds_idx = idx * val_batch_size
        current_item = val_volume_ds[ds_idx]
        print('check val data:')
        print(current_item, 'image:', val_check_data['image'].shape, 'label:', val_check_data['label'].shape)

def transform_datasets_to_2d(train_ds, val_ds, saved_name_train, saved_name_val, batch_size=8,ifsave=True):
    # Load 2D slices of CT images
    train_ds_2d = []
    val_ds_2d = []
    shape_list_train = []
    shape_list_val = []
    all_slices_train=0
    all_slices_val=0

    # Load 2D slices for training
    for sample in train_ds:
        train_ds_2d_image = LoadImaged(keys=["image", "label"],image_only=True, ensure_channel_first=False, simple_keys=True)(sample)
        train_ds_2d_image=DivisiblePadd(["image", "label"], (-1,batch_size), mode="minimum")(train_ds_2d_image)
        name = os.path.basename(os.path.dirname(sample['image']))
        num_slices = train_ds_2d_image["image"].shape[-1]
        #print(train_ds_2d_image["image"].shape)
        #print(num_slices)
        shape_list_train.append({'patient': name, 'shape': train_ds_2d_image["image"].shape})
        for i in range(num_slices):
            train_ds_2d.append({'image': train_ds_2d_image['image'][:,:,i], 'label': train_ds_2d_image['label'][:,:,i]})
        all_slices_train += num_slices

    # Load 2D slices for validation
    for sample in val_ds:
        val_ds_2d_image = LoadImaged(keys=["image", "label"],image_only=True, ensure_channel_first=False, simple_keys=True)(sample)
        val_ds_2d_image=DivisiblePadd(["image", "label"], (-1, batch_size), mode="minimum")(val_ds_2d_image)
        name = os.path.basename(os.path.dirname(sample['image']))
        shape_list_val.append({'patient': name, 'shape': val_ds_2d_image["image"].shape})
        num_slices = val_ds_2d_image["image"].shape[-1]
        for i in range(num_slices):
            val_ds_2d.append({'image': val_ds_2d_image['image'][:,:,i], 'label': val_ds_2d_image['label'][:,:,i]})
        all_slices_val += num_slices
    # Save shape list to csv
    if ifsave:
        np.savetxt(saved_name_train,shape_list_train,delimiter=',',fmt='%s',newline='\n') # f means format, r means raw string
        np.savetxt(saved_name_val,shape_list_val,delimiter=',',fmt='%s',newline='\n') # f means format, r means raw string
    return train_ds_2d, val_ds_2d, all_slices_train, all_slices_val, shape_list_train, shape_list_val

def get_train_val_loaders(train_ds_2d, val_ds_2d, batch_size, val_batch_size,resized_size=(256,256)):
    # Define transforms
    '''
    normalize='zscore'
    div_size=(16,16,None)
    train_transforms = get_transforms(normalize,resized_size,div_size)
    '''

    train_transforms = Compose(
        [
            EnsureChannelFirstd(keys=["image", "label"]),
            #ThresholdIntensityd(keys=["image"], threshold=1500, above=False, cval=0.0),
            #ThresholdIntensityd(keys=["image"], threshold=-1000, above=True, cval=0.0),
            NormalizeIntensityd(keys=["image", "label"], nonzero=False, channel_wise=True), # z-score normalization
            ResizeWithPadOrCropd(keys=["image", "label"], spatial_size=resized_size,mode="minimum"),
            Rotate90d(keys=["image", "label"], k=3),
            DivisiblePadd(["image", "label"], 16, mode="minimum"),
        ]
    )
    train_transforms_list=train_transforms.__dict__['transforms']
    # Create training dataset and data loader
    train_dataset = Dataset(data=train_ds_2d, transform=train_transforms)
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=False, num_workers=0, pin_memory=True)

    val_batch_size = val_batch_size
    # Create validation dataset and data loader
    val_dataset = Dataset(data=val_ds_2d, transform=train_transforms)
    val_loader = DataLoader(val_dataset, batch_size=val_batch_size, shuffle=False, num_workers=0, pin_memory=True)
    return train_loader, val_loader, train_transforms_list,train_transforms

def mydataloader(data_pelvis_path,train_number,val_number,batch_size,val_batch_size,saved_name_train='./train_ds_2d.csv',saved_name_val='./val_ds_2d.csv',resized_size=(256,256)): 
    train_ds, val_ds = get_file_list(data_pelvis_path, 
                                     train_number, 
                                     val_number)
    train_ds_2d, val_ds_2d,\
    all_slices_train,all_slices_val,\
    shape_list_train,shape_list_val = transform_datasets_to_2d(train_ds, val_ds, 
                                                            saved_name_train, 
                                                            saved_name_val,
                                                            batch_size=batch_size,
                                                            ifsave=False)
    train_loader, val_loader, \
    train_transforms_list,train_transforms = get_train_val_loaders(train_ds_2d, 
                                                                val_ds_2d, 
                                                                batch_size=batch_size, 
                                                                val_batch_size=val_batch_size,
                                                                resized_size=resized_size)
    return train_loader,val_loader,\
            train_transforms_list,train_transforms,\
            all_slices_train,all_slices_val,\
            shape_list_train,shape_list_val