INPUT_OBJ_PATH=$1
INPUT_2D_PATH=$2
OUTPUT_FILENAME=$3
OUTPUT_DIR=$4
STYLE_WEIGHT=$5
CONTENT_WEIGHT=$6
NUM_ITERS=$7
LR_VERTICES=$8
LR_TEXTURES=$9
TEXTURE_SIZE=${10}
IMAGE_SIZE=${11}

#cd 2D_3D_style_dream_neural_renderer/

cd 2d_3d_style_dream_neural_renderer

python ./run_examples_style_transfer_3d/run.py \
    --filename_mesh ${INPUT_OBJ_PATH} \
    --filename_style ${INPUT_2D_PATH} \
    --filename_output ${OUTPUT_DIR}/${OUTPUT_FILENAME} \
    --lambda_style ${STYLE_WEIGHT} \
    --lambda_content ${CONTENT_WEIGHT} \
    --num_iteration ${NUM_ITERS} \
    --lr_vertices ${LR_VERTICES} \
    --lr_textures ${LR_TEXTURES} \
    --texture_size ${TEXTURE_SIZE} \
    --image_size ${IMAGE_SIZE} 