from my_dataset import mydataloader
if __name__ == '__main__':
    data_pelvis_path = r'C:\Users\56991\Projects\Datasets\Task1\pelvis'
    train_loader,val_loader,\
    train_transforms_list,train_transforms,\
    all_slices_train,all_slices_val,\
    shape_list_train,shape_list_val = mydataloader(data_pelvis_path,
                                                train_number=2,
                                                val_number=1,
                                                batch_size=8,
                                                val_batch_size=1,
                                                saved_name_train='./train_ds_2d.csv',
                                                saved_name_val='./val_ds_2d.csv',
                                                resized_size=(256,256))
    # test one sample from train_loader
    for i, data in enumerate(train_loader):
        print(i)
        print(data['image'].shape)
        print(data['label'].shape)
        break
    # test one sample from val_loader
    for i, data in enumerate(val_loader):
        print(i)
        print(data['image'].shape)
        print(data['label'].shape)
        break