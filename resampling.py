#!/usr/bin/env python

import numpy as np
import matplotlib.pyplot as plt
from PIL import Image

# Utilities
def read_png_file(filename):
    png=Image.open(filename)
    image_array=np.array(png.getdata(),np.uint8).reshape(png.size[1], png.size[0])
    return image_array.astype('float32')

def array_to_image(array):
    minimal_value=np.min(array)
    maximal_value=np.max(array)
    if minimal_value < 0 or maximal_value > 255:
        array = 255*(array-minimal_value)/(maximal_value-minimal_value)
    array_uint8=array.astype('uint8')
    return Image.fromarray(array_uint8, 'L')
                    
def save_png_file(array,filename):
    png=array_to_image(array)
    png.save(filename)

def display_image(array):
    png=array_to_image(array)
    png.show()


# Nearest neighbor interpolation
def resampling_nn(reference,
                  floating,
                  transformation,
                  padding):
    # Create an empty image based on the reference image discretisation space
    warped_image=np.zeros(reference.shape)
    reference_position=np.array([0,0,1])
    # Iterate over all pixel in the reference image
    for j in range(0,reference.shape[1]):
        reference_position[1]=j
        for i in range(0,reference.shape[0]):
            reference_position[0]=i
            # Compute the corresponding position in the floating image space
            floating_position=transformation.dot(reference_position)
            # Nearest neighbour interpolation
            if floating_position[0]>=0 and \
                floating_position[1]>=0 and \
                floating_position[0]<=reference.shape[0]-1 and \
                floating_position[1]<=reference.shape[1]-1:
                floating_position[0]=np.round(floating_position[0])
                floating_position[1]=np.round(floating_position[1])
                warped_image[i][j]=floating[floating_position[0]][floating_position[1]]
            else:
                warped_image[i][j]=padding
    return warped_image
    
# Nearest neighbor interpolation
def resampling_nn_fast(reference,
                       floating,
                       transformation):
    # Compute the deformation field
    ref_def = np.ones([3,reference.size])
    ref_def[0:2,:] = np.mgrid[0:reference.shape[0],0:reference.shape[1]].reshape(2,reference.size)
    flo_def=transformation.dot(ref_def)
    
    # Compute the nearest indices
    pre = np.round(flo_def).astype('int')
    indices = pre[0,:] * floating.shape[1] + pre[1,:]

    # Cheap boundary conditions
    indices[indices<0]=0
    indices[indices>=floating.size]=floating.size-1

    # Weighted sum
    warped_image = floating.ravel()[indices]
    return warped_image.reshape(reference.shape)

# Linear interpolation
def resampling_ln(reference,
                  floating,
                  transformation,
                  padding):
        # Create an empty image based on the reference image discretisation space
    warped_image=np.zeros(reference.shape)
    reference_position=np.array([0,0,1])
    # Iterate over all pixel in the reference image
    for j in range(0,reference.shape[1]):
        reference_position[1]=j
        for i in range(0,reference.shape[0]):
            reference_position[0]=i
            # Compute the corresponding position in the floating image space
            floating_position=transformation.dot(reference_position)
            # Nearest neighbour interpolation
            if floating_position[0]>0 and \
                floating_position[1]>0 and \
                floating_position[0]<reference.shape[0]-1 and \
                floating_position[1]<reference.shape[1]-1:
                #do linear interpolation
                x_weight=floating_position[0]-np.floor(floating_position[0])
                y_weight=floating_position[1]-np.floor(floating_position[1])
                floating_position[0]=np.floor(floating_position[0])
                floating_position[1]=np.floor(floating_position[1])                    
                x1_weighted=(1-x_weight)*(1-y_weight)*floating[floating_position[0]][floating_position[1]]
                x2_weighted=(x_weight)*(1-y_weight)*floating[floating_position[0]+1][floating_position[1]]
                y1_weighted=(1-x_weight)*(y_weight)*floating[floating_position[0]][floating_position[1]+1]
                y2_weighted=(x_weight)*(y_weight)*floating[floating_position[0]+1][floating_position[1]+1]
                warped_image[i][j]=x1_weighted+x2_weighted+y1_weighted+y2_weighted
            else:
                warped_image[i][j]=padding
    return warped_image

# Linear interpolation
def resampling_ln_fast(reference,
                       floating,
                       transformation):
    ref_def = np.ones([3,reference.size])
    ref_def[0:2,:] = np.mgrid[0:reference.shape[0],0:reference.shape[1]].reshape(2,reference.size)
    flo_def=transformation.dot(ref_def)
    
    pre = np.floor(flo_def).astype('int')
    ratio = flo_def - pre.astype('float')
    indices_a = pre[0,:] * floating.shape[1] + pre[1,:]
    indices_b = pre[0,:] * floating.shape[1] + pre[1,:] + 1
    indices_c = (pre[0,:]+1) * floating.shape[1] + pre[1,:]
    indices_d = (pre[0,:]+1) * floating.shape[1] + pre[1,:] + 1

    # Cheap boundary conditions
    indices_a[indices_a<0]=0
    indices_b[indices_b<0]=0
    indices_c[indices_c<0]=0
    indices_d[indices_d<0]=0
    indices_a[indices_a>=floating.size]=floating.size-1
    indices_b[indices_b>=floating.size]=floating.size-1
    indices_c[indices_c>=floating.size]=floating.size-1
    indices_d[indices_d>=floating.size]=floating.size-1

    # Weighted sum
    warped_image = \
        floating.ravel()[indices_a] * (1-ratio[0,:]) * (1-ratio[1,:]) + \
        floating.ravel()[indices_b] * (1-ratio[0,:]) * ratio[1,:] + \
        floating.ravel()[indices_c] * ratio[0,:] * (1-ratio[1,:]) + \
        floating.ravel()[indices_d] * ratio[0,:] * ratio[1,:]
    return warped_image.reshape(reference.shape)


# Sum squared difference
def ssd(img1, img2):
    return np.sum(np.square(img1-img2))

# Normalised cross correlation
def ncc(img1, img2):
	mean1=np.mean(img1)
	mean2=np.mean(img2)
	result=np.sum((img1-mean1)*(img2-mean2))
    return result
    

# Normalised mutual information
def nmi(img1, img2):
    # TODO
    return None

# Main function
def main():
    # Read an input image
    reference_image=read_png_file('./BrainWeb_2D.png')
    floating_image=read_png_file('./BrainWeb_2D.png')
    
    # Generate and apply a transformation
    translation_values=np.arange(-2,2,0.05,dtype='float')
#    translation_values=np.array([-2])
    transformation_matrix=np.eye(3,3)
    ssd_values_nn=np.ndarray(len(translation_values))

    # Apply successive translations
    for i in range(0,len(translation_values)):
        print('Perform resampling '+str(i+1)+'/'+str(len(translation_values)))
        transformation_matrix[0][2]=translation_values[i]
        warped_image_nn=resampling_ln_fast(reference_image,
                                                floating_image,
                                                transformation_matrix)
        #ssd_values_nn[i]=ssd(reference_image,warped_image_nn)
		ncc_values_ln[i]=ncc(reference_image,warped_image_nn)

    # Display the results
    plt.subplot(1, 1, 1)
    plt.plot(translation_values, ncc_values_nn, 'b-', label='linear interpolation')
    plt.legend(loc='best', numpoints=1, fontsize='small')
    plt.xlabel('Translation (in voxel)')
    plt.ylabel('SSD value')
    plt.show()

    # Display an image
#    display_image(warped_image)
    # Save the warped image
#    save_png_file(warped_image, 'filename.png')
    # Save the plot
#    fig.savefig('filename.pdf', format='PDF')

if __name__ == "__main__":
    main()    
