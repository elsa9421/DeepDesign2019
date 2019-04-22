

import os
os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"   # see issue #152
os.environ["CUDA_VISIBLE_DEVICES"]="1"
import keras
from keras import applications
from keras import backend as K
import tensorflow as tf
import numpy as np
import scipy 
from scipy.misc import imsave
from keras.applications.vgg16 import decode_predictions, preprocess_input
from keras.preprocessing.image import ImageDataGenerator
import glob
import pdb 
import math
#import cv2
'''
----------------------------------
Building-relevant ImageNet classes
----------------------------------
park bench
altar
triumphal arch
patio
steel arch bridge
suspension bridge
viaduct
barn
greenhouse
palace
monastery
library
apiary
boathouse
church
mosque
stupa
planetarium
restaurant
cinema
home theater
lumbermill
coil
obelisk
totem pole
castle
prison
grocery store
bakery
barbershop
bookshop
butcher shop
confectionery
shoe shop
tobacco shop
toyshop
fountain
cliff dwelling
yurt
dock
megalith
bannister
breakwater
dam
chainlink fence
picket fence
worm fence
stone wall
mountain tent
pedestal
tile roof
water tower 
stage 
dome 
vault 
'''

## --------------------------------------
## Helper functions
## --------------------------------------
#
# util function to convert a tensor into a valid image
def deprocess_image(x):
    #
    # normalize tensor: center on 0., ensure std is 0.1
    x -= x.mean()
    x /= (x.std() + 1e-5)
    x *= 0.1
    # clip to [0, 1]
    x += 0.5
    x = np.clip(x, 0, 1)
    #
    # convert to RGB array
    x *= 255
    #
    x = np.clip(x, 0, 255).astype('uint8')
    return x

def make_labels_dict(classes):
    num_classes = len(classes)
    class_dict = {}
    #
    for ind_, class_ in enumerate(classes):
        temp_vec = np.zeros(num_classes)
        temp_vec[ind_] = 1
        class_dict[class_] = temp_vec
        #
    return class_dict 

def generate_arrays_from_file(file_list, batch_size, class_labels_dict):
    batch_file_inds = np.random.choice(len(file_list), batch_size)
    #for ind_ in batch_file_inds:
    #    # create numpy arrays of input data
    #    # and labels, from each line in the file
    #    #x1, x2, y = process_line(line)
    #    #image_ = scipy.misc.imread(img_file)
    #    #image_ = scipy.misc.imresize(image_,(400,600))
    #    #label_ = np.array([class_labels_dict[label_key] for label_key in class_labels_dict if label_key in img_file])
    i = 0
    INPUT_SHAPE = (400,600)
    while True:
        image_batch = []
        label_batch = []
        for b in range(batch_size):
            if i == len(file_list):
                i = 0
                np.random.shuffle(file_list)
            img_file = file_list[i]
            i += 1
            image = scipy.misc.imresize(scipy.misc.imread(img_file), INPUT_SHAPE)
            image_batch.append((image.astype(float)/255.0))
            label = [class_labels_dict[label_key] for label_key in class_labels_dict if label_key in img_file]
            label_batch.append(label[0])
            #
        image_batch = np.array(image_batch)
        label_batch = np.array(label_batch)
        #pdb.set_trace()
        yield image_batch, label_batch

def finetune_vgg16(train_folder_path, image_shape, classes, num_epochs):
    ##
    class_labels_dict = make_labels_dict(classes)
    num_classes = len(classes)
    ##
    ## define input of model
    #image_shape = (None, None, 3)
    ##inp=keras.layers.Input(shape =image_shape)
    ##
    ## build the VGG16 network for variable image sizes
    base_model = applications.VGG16(include_top=False, weights='imagenet', input_shape=image_shape)
    ## add layers specific to our task
    x=base_model.output
    x = keras.layers.GlobalAveragePooling2D()(x)
    x = keras.layers.Dense(4096, activation='relu', name='fc1')(x)
    x = keras.layers.Dense(4096, activation='relu', name='fc2')(x)
    predictions = keras.layers.Dense(num_classes, activation='softmax', name='predictions')(x)
    ##
    custom_model = keras.Model(inputs=base_model.input,outputs=predictions)
    # Make sure that the pre-trained bottom layers are not trainable
    for layer in custom_model.layers[:7]:
        layer.trainable = False
    adam_opt = keras.optimizers.Adam(lr=1e-5)
    custom_model.compile(optimizer=adam_opt,loss='categorical_crossentropy',metrics=['accuracy'])

    ## get list of all training data
    #all_data = glob.glob('{}/*/*'.format(train_folder_path))
    all_data = glob.glob('{}/*'.format(train_folder_path))
    #with open('/data_file.txt','w') as f:
    #    f.write('\n'.join(all_data))
    #
    #train_data = all_data[10:]
    #test_data = all_data[:10]
    #num_iters = len(train_data)//batch_size
    #iter_counter = 0
    #
    ## set up dataset generatpr
    train_datagen=ImageDataGenerator(preprocessing_function=preprocess_input) #included in our dependencies
    train_generator=train_datagen.flow_from_directory(train_folder_path,
                                                     target_size=image_shape,
                                                     color_mode='rgb',
                                                     batch_size=32,
                                                     class_mode='categorical',
                                                     shuffle=True)
    # generate_arrays_from_file(all_data, batch_size, class_labels_dict)
    #
    ##  train the network
    STEP_SIZE_TRAIN=train_generator.n//train_generator.batch_size
    #pdb.set_trace()
    custom_model.fit_generator(train_generator, 
                                steps_per_epoch=STEP_SIZE_TRAIN, 
                                epochs=num_epochs, 
                                verbose=1)
    ## save the network weights
    custom_model.save_weights('vgg16_custom_model_weights_400x600.h5')
    ## Save the model architecture
    with open('model_architecture.json', 'w') as f:
        f.write(custom_model.to_json())
    #    ##

def center_crop_image(input_img_data_full, new_shape=(224,224)):
    #
    hcrop, wcrop = new_shape
    h,w,c = input_img_data_full.shape
    top = int(math.floor((h-hcrop)/2.0))
    bottom = int(math.ceil((h+hcrop)/2.0))
    left = int(math.floor((w-wcrop)/2.0))
    right = int(math.ceil((w+wcrop)/2.0))
    input_img_data = input_img_data_full[top:bottom,left:right,:]
    return input_img_data

############################################################################
########################### MAIN PROGRAM ###################################
############################################################################

## --------------------------------------
## Train the model for class optimization
## --------------------------------------
#train_model = True
train_model = False
if train_model:
    ## finetune vgg16 model on dataset
    num_epochs = 25
    train_folder_path = '/building_motif_dataset/train'
    image_shape = (400,600,3)
    classes = ['arch', 'bench', 'boulder', 'cinderblock', 'ditch', 'fountain', 'stairs', 'steppingstone']
    finetune_vgg16(train_folder_path, image_shape, classes, num_epochs)
    pdb.set_trace()

## --------------------------------------
## Load in the pretrained VGG16 model
## --------------------------------------

## choose if you upload the vgg16 network traned on imagenet weights or imagenet weights finetuned on a custom dataset
#which_vgg16_model = 'imagenet'
which_vgg16_model = 'custom'

## create the results directory
results_dir ='results_%s'%(which_vgg16_model)
if not os.path.exists(results_dir):
    os.mkdir(results_dir)

## load in the pretrained vgg16 model to use for dreaming
if which_vgg16_model=='imagenet':
    ##
    ## input shape for pretrained vgg16 network
    input_shape = (224,224,3)
    ## build the VGG16 network
    model = applications.VGG16(include_top=True, weights='imagenet')
    ## build dictionary of layers
    layer_dict = dict([(layer.name, layer) for layer in model.layers])
    ## Print out the model architecture
    model.summary()
    ## get the list of imagenet classes
    #output_classes = vgg16.decode_predictions(np.expand_dims(np.arange(1000), axis=0), top=1000)
    output_classes = decode_predictions(np.expand_dims(np.arange(1000), axis=0), top=1000)
    num_classes = len(output_classes[0])
    #pdb.set_trace()
    all_classes_index_dict = {tup_[1]:tup_[2] for tup_ in output_classes[0]}
    #
    ## get the desired class and the corresponding output index
    output_index= all_classes_index_dict[desired_class]
    #
else:
    #
    ## input shape for the custom pretrained vgg16 network
    input_shape = (400,600,3)
    #
    weights_file = 'vgg16_custom_model_weights_400x600.h5'
    arch_file = 'model_architecture.json'
    #
    from keras.models import model_from_json
    ## Model reconstruction from JSON file
    with open(arch_file, 'r') as f:
        model = model_from_json(f.read())
        #
    ## Load weights into the new model
    model.load_weights(weights_file)
    #
    output_classes = ['arch', 'bench', 'boulder', 'cinderblock', 'ditch', 'fountain', 'stairs', 'steppingstone']
    num_classes = len(output_classes)
    all_classes_index_dict = {y:i for i, y in enumerate(output_classes)}
    ## get the desired class and the corresponding output index
    output_index = all_classes_index_dict[desired_class]
    print("Loaded vgg16 model finetuned on custom dataset from disk")
    #

## --------------------------------------
## Build the model for class optimization
## --------------------------------------

## choose the desired imageNet class or custom class
## image net classes
#desired_class = 'dome'
#
## custom trained classes
desired_class = 'arch'
#desired_class = 'bench'
#desired_class = 'boulder'
#desired_class = 'cinderblock'
#desired_class = 'ditch'
#desired_class = 'fountain'
#desired_class = 'stairs'
#desired_class = 'steppingstone'

reg=0.01
## get the weights of the prediction layer
weights=model.get_layer('predictions').get_weights()
kernel=weights[0]
bias=weights[1]  
#
layer_name = 'fc2'
intermediate_layer_model = keras.models.Model(inputs=model.get_input_at(0), outputs=model.get_layer(layer_name).output)
inp=keras.layers.Input(shape =input_shape)
x=intermediate_layer_model(inp)
#
model1=keras.layers.Dense(num_classes, 
                          activation=None, 
                          use_bias=True, 
                          kernel_initializer=tf.constant_initializer(kernel), 
                          bias_initializer=tf.constant_initializer(bias))(x)  
                          #
## compute the gradient of the input picture wrt this loss
input_img=keras.layers.Input(shape =input_shape)
x=intermediate_layer_model(input_img)
x=keras.layers.Dense(num_classes, activation=None, use_bias=True, kernel_initializer=tf.constant_initializer(kernel), bias_initializer=tf.constant_initializer(bias))(x)  
model1=keras.models.Model(inputs=input_img,outputs=x)
#input_img=tf.Variable(np.random.random((1, 3, 224, 224)) * 20 + 128)
loss = K.mean(model1(input_img)[:, output_index])- reg*K.mean(K.square(input_img))
grads = K.gradients(loss, input_img)[0]
## normalization trick: we normalize the gradient
#grads /= (K.sqrt(K.mean(K.square(grads))) + 1e-5)
## this function returns the loss and grads given the input picture
iterate = K.function([input_img], [loss, grads])

## -------------------------------
## Load input image(s) to dream on 
## -------------------------------

## flags that allow you to center crop or resize the input image
crop_dream_input = False
resize_dream_input = True

## Choose if you want to dream on noise, a single image, or a directory of images
#dream_input = 'noise'
#dream_input = '/root/single_image.jpg'
dream_input = '/root/multi_images'

if dream_input=='noise':
    ## we start from a gray image with some noise
    imh = input_shape[0]
    imw = input_shape[1]
    imc = input_shape[2]
    input_img_data = np.random.random((1, imh, imw, imc))*255# * 20 + 128.
    #input_img_data = input_img_data*20 +128   
    img_list = [input_img_data]    
    dream_input_ids = ['noise']   
    #
elif os.path.isfile(dream_input):
    ## Load in image 
    #img_file = '/home/alexandracarlson/Desktop/Robotics_Building_networks/Matias_garden_model/images/190319_Basemodel50050.jpg'
    input_img_data_full = scipy.misc.imread(dream_input)
    #
    if resize_dream_input:
        ## resize the full image
        input_img_data = scipy.misc.imresize(input_img_data_full, input_shape)
        #
    if crop_dream_input:
        ## get a partial crop of the image
        input_img_data = center_crop_image(input_img_data_full, new_shape=(input_shape[0],input_shape[1]))
        #
    img_list = [np.expand_dims(input_img_data.astype(float),axis=0)]
    dream_input_ids = [os.path.split(os.path.splitext(imgf)[0])[1]]
    #
elif os.path.isdir(dream_input):
    img_list = []
    dream_input_ids = []
    ## load in a directory of images
    for imgf in sorted(os.listdir(dream_input)):
        img_ = scipy.misc.imread(os.path.join(dream_input,imgf))
        if crop_dream_input:
            ## crop images
            input_img_data = center_crop_image(img_, new_shape=(input_shape[0],input_shape[1]))
            #
        if resize_dream_input:
            ## resize the full image
            input_img_data = scipy.misc.imresize(img_, input_shape)
            #
        img_list.append(np.expand_dims(input_img_data.astype(float), axis=0))
        dream_input_ids.append(os.path.split(os.path.splitext(imgf)[0])[1])
else:
    print('Incorrect/bad path given for input image(s)')
   

## -------------------------------
## Perform class optimization     
## -------------------------------  
num_iters = 300   
## preprocess input data based upon vgg-16
#input_img = preprocess_input(input_img_data)
#
# run gradient ascent for 200 steps
for input_img_data, dream_input_id in zip(img_list, dream_input_ids):
    #
    input_img = preprocess_input(input_img_data)
    #
    for iter_ in range(num_iters):
        loss_value, grads_value = iterate([input_img])
        input_img += grads_value *1
        #
        if(iter_%500000==0):
            #print(loss_value)
            ## save image for this iteration
            img = input_img_data[0]
            img = deprocess_image(img)
            #input_img_data_full[top:bottom,left:right,:] = img
            #imsave(os.path.join(results_dir, '%s_%s_iter_%d.png' %(dream_input_id, desired_class, iter_)), img)
            #
    img = input_img[0]
    img = deprocess_image(img)
    imsave(os.path.join(results_dir, '%s_dreamed_%s_final.png' %(dream_input_id, desired_class)), img)
    print('finished %s'%(dream_input_id))
    #pdb.set_trace()
#img = input_img_data[0]
#img = deprocess_image(img)
#print(img.shape)
#
## save the final image
#imsave(os.path.join(results_dir, '%s_%s_iter_%d.png' %(image_type, desired_class, num_iters)), img)

