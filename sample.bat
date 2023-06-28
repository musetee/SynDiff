@echo off

set BASIC_FLAGS=--image_size 256 --exp origin --num_channels 2 
set MODEL_FLAGS=--num_channels_dae 64 --ch_mult 1 1 2 2 4 4 --num_timesteps 4 --num_res_blocks 2 --batch_size 1 --embedding_type positional  --z_emb_dim 256
set TEST_FLAGS=--contrast1 T1  --contrast2 T2 --which_epoch 50 --gpu_chose 0 --input_path C:\Users\56991\Projects\SynDiff\SynDiff_sample_data --output_path C:\Users\56991\Projects\SynDiff\output

call C:\Users\56991\Environments\torch\venv\Scripts\activate

python test.py %BASIC_FLAGS% %MODEL_FLAGS% %TEST_FLAGS%

pause