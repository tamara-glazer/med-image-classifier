#============================================================================#
# MANUAL FEATURE CREATION
#============================================================================#

import numpy as np
import pandas as pd
import os, pydicom, cv2
import matplotlib.pyplot as plt

from scipy import ndimage
from skimage import exposure
from skimage.filters import gaussian
from skimage.filters import try_all_threshold
from skimage import data, img_as_float
from skimage.segmentation import (morphological_chan_vese,
                                  morphological_geodesic_active_contour,
                                  inverse_gaussian_gradient,
                                  checkerboard_level_set,
                                  chan_vese,
                                  active_contour)
from skimage.util.shape import view_as_blocks                                  
from skimage.filters import threshold_otsu
from skimage.filters import sobel
from skimage.filters import sobel_h
from skimage.filters import sobel_v
from skimage.filters import scharr_h
from skimage.filters import scharr_v
from skimage.segmentation import clear_border
from skimage.measure import label, regionprops
from skimage.morphology import closing, square, disk, opening
from skimage.color import label2rgb
from skimage.transform import hough_line
from sklearn.utils.testing import ignore_warnings
from skimage.color import label2rgb
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import minmax_scale
from skimage.feature import hog
from skimage import data, exposure
from skimage.util import img_as_float
from skimage.filters import gabor_kernel
from skimage.filters import gaussian
from skimage.segmentation import active_contour
from skimage.filters import threshold_mean
from skimage.feature import canny
from scipy import ndimage
from skimage.transform import hough_line, hough_line_peaks

import preprocess as p
import features_ROI as adf

pd.set_option('display.max_columns', 500)
@ignore_warnings(category=FutureWarning)
def apply_contour(img):
    '''
    Active contour from skimage
    '''

    s = np.linspace(0, 2*np.pi, 400)
    r = 100 + 100*np.sin(s)
    c = 220 + 100*np.cos(s)
    init = np.array([r, c]).T
    snake = active_contour(gaussian(img, 3),
                       init, alpha=0.015, beta=10, gamma=0.001,
                       coordinates='rc')
    fig, ax = plt.subplots(figsize=(7, 7))
    ax.imshow(img, cmap=plt.cm.gray)
    ax.plot(init[:, 0], init[:, 1], '--r', lw=3)
    ax.plot(snake[:, 0], snake[:, 1], '-b', lw=3)
    ax.set_xticks([]), ax.set_yticks([])
    ax.axis([0, a8.shape[1], a8.shape[0], 0])
    plt.show()

def store_evolution_in(lst):
    """Returns a callback function to store the evolution of the level sets in
    the given list.
    """

    def _store(x):
        lst.append(np.copy(x))

    return _store

def apply_ACWE(img):
    '''
    '''
    image = img_as_float(img)
    init_ls = checkerboard_level_set(image.shape, 6)
    # List with intermediate results for plotting the evolution
    evolution = []
    callback = store_evolution_in(evolution)
    ls = morphological_chan_vese(image, 35, init_level_set=init_ls, smoothing=3,
                                 iter_callback=callback)
    
    fig, axes = plt.subplots(2, 2, figsize=(8, 8))
    ax = axes.flatten()
    ax[1].imshow(ls, cmap="gray")
    ax[1].set_axis_off()
    contour = ax[1].contour(evolution[2], [0.5], colors='g')
    contour.collections[0].set_label("Iteration 2")
    contour = ax[1].contour(evolution[7], [0.5], colors='y')
    contour.collections[0].set_label("Iteration 7")
    contour = ax[1].contour(evolution[-1], [0.5], colors='r')
    contour.collections[0].set_label("Iteration 35")
    ax[1].legend(loc="upper right")
    title = "Morphological ACWE evolution"
    ax[1].set_title(title, fontsize=12)


# label image regions
def define_region(img):
    '''
    '''
    labels = label(img)
    largestCC = labels == np.argmax(np.bincount(labels.flat, weights=img.flat))
    return largestCC

def compute_sobel(img, mask = None):
    '''
    Compute the gradient direction and magnitude using Sobel filter 
    Takes: image pixel array, optional mask
    Returns: array of angles
    '''

    s_h = sobel_h(img, mask = mask)
    s_v = sobel_v(img, mask = mask)
    return np.arctan2(s_v, s_h), np.sqrt(s_v**2 + s_h**2)

def compute_scharr(img, mask = None):
    '''
    Compute the gradient direction and magnitude using Scharr filter 
    Takes: segmented image array
    Returns: array of angles
    '''

    s_h = scharr_h(img, mask = mask)
    s_v = scharr_v(img, mask = mask)
    return np.arctan2(s_v, s_h), np.sqrt(s_v**2 + s_h**2)


def compute_gradient_std(theta, magnitude):
    '''
    Takes: array of angles and array of magnitudes from Sobel/Scharr
    Returns: standard deviation of normalized magnitude-angle distribution
    '''

    avg = np.mean(magnitude)
    # print("average magnitude is ", avg)
    x_dim, y_dim = theta.shape

    t = theta.reshape((x_dim * y_dim, 1))
    m = magnitude.reshape((x_dim * y_dim, 1))
    df = pd.DataFrame(np.hstack((t, m)), columns = ["theta", "magnitude"])

    if avg != 0:
        edge_gradient_dist = df.groupby(['theta'], as_index=False).sum() / avg
        return edge_gradient_dist['magnitude'].std()
    
    else: 
        return 0


def get_border_pixels(mask):
    '''
    Extract the pixels on the border of a region
    Takes: segmented mask
    Returns: array mask where border pixels are 1, all others 0
    '''

    distance = ndimage.distance_transform_edt(mask)
    distance[distance == 0] = 0
    distance[distance > 3] = 0 # take a 3 pixel border...
    return distance


# TO DO: try more of the neighborhoods in Huo and Giger (1995)
def compute_spiculation(orig, segmented_mask):
    
    # filter approach based on Huo and Giger (1995)
    # they use Sobel but Scharr is supposed to be rotation invariant (?)
    theta_A, magnitude_A = compute_scharr(orig, mask = segmented_mask)
    std_dev_A = compute_gradient_std(theta_A, magnitude_A)

    # B: just use a 3? pixel border
    border_mask = get_border_pixels(segmented_mask)
    theta_B, magnitude_B = compute_scharr(orig, mask = border_mask)
    std_dev_B = compute_gradient_std(theta_B, magnitude_B)

    # C: use the whole ROI 
    # ideally would reduce to 20 pixel adjacent area but not working right now
    # ymin, xmin, ymax, xmax = regionprops(segmented_mask[0]).bbox
    # bbox_mask = np.zeros(orig.shape)
    # bbox_mask[ymin:ymax, xmin:xmax] = 1
    # region_bbox = orig * bbox_mask
    theta_C, magnitude_C = compute_scharr(orig)
    std_dev_C = compute_gradient_std(theta_C, magnitude_C)

    # D: use non-region ROI after applying opening (circular, arbitrary size right now)
    open_nonregion = opening(np.where(segmented_mask == 0, 1, 0), disk(5))
    theta_D, magnitude_D = compute_scharr(orig, mask = open_nonregion)
    std_dev_D = compute_gradient_std(theta_D, magnitude_D)

    # higher standard deviation here indicates more spiculation
    return {'A': std_dev_A, 'B': std_dev_B, 'C': std_dev_C, 'D': std_dev_D}
 

def circular_mask(matrix, center, radius):
    '''
    Given an image, a center point, and a diameter, returns a copy of the
    original image only displaying the values within a circle centered at
    "center" with radius equal to (diameter - 1) / 2.

    Input:
        matrix (numpy array): a numpy array of the original image
        center (lst): row and column of the center pixel to evaluate
        diameter (int): odd integer value

    Return:
        matrix_copy (numpy array): a copy of the original image with a
                                   circular mask applied
    '''
    # Create a mask given center pixel and diameter
    h = matrix.shape[0]
    w = matrix.shape[1]
    radius = int(radius)
    y, x = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((x - center[0]) ** 2 + (y - center[1]) ** 2)
    mask = dist_from_center <= radius
    empty_image = np.zeros((matrix.shape[0], matrix.shape[1]))
    matrix_copy = matrix.copy()
    matrix_copy[~mask] = 2

    return matrix_copy


def compute_circularity(filled):
    '''
    Computes circularity given an image with one region.
    '''
    label_image = label(filled)
    regions = regionprops(label_image)
    # Find center of mass
    y0, x0 = regions[0].centroid
    # Find area of segment
    area = regions[0].area
    # Create circle with this area
    radius = np.sqrt(area / np.pi)
    masked_image = circular_mask(filled, [x0, y0], radius) # Visualize this
    # Calculate circularity
    overlap = np.count_nonzero(masked_image == 1)
    rest_of_circle = np.count_nonzero(masked_image == 0)
    circularity = overlap / (overlap + rest_of_circle)

    return circularity


###### PARTH FEATURES #########

def helper_convert_scale_alpha(maxval):
    '''
    Helper function to convert Image Scale
    Returns: rescaled array
    '''
    return 255.0/maxval

def helper_plot_comparison(orig, filtered):
    '''
    Compare plots juxtaposed
    '''
    fig,axes = plt.subplots(1, 2)
    fig.set_size_inches([12, 9])
    axes[0].imshow(orig, cmap='gray')
    axes[0].set_title('original')
    axes[1].imshow(filtered, cmap='gray')
    axes[1].set_title('filtered')

def helper_bbox(img):
    '''
    Returns: Bounding Box over ROI and Segmented region
    used in subsequent function get_iou

    '''

    a = np.where(img != 0)
    bbox = np.min(a[0]), np.max(a[0]), np.min(a[1]), np.max(a[1])
    return bbox

def generate_iou(original, segmented_mask):
    '''
    Get intersection area using bounding box defined on area
    Note: The dimensions of superset (A) is considered as those of main ROI
    PS: DICE did not have much variance 
    Returns: intersected area
    '''
    orig = original.pixel_array
    boxA = np.array(helper_bbox(orig))
    boxB = np.array(helper_bbox(segmented_mask))

    xA = max(boxA[0], boxB[0]) + 1
    yA = max(boxA[1], boxB[1]) + 1
    xB = min(boxA[2], boxB[2]) + 1
    yB = min(boxA[3], boxB[3]) + 1

    # compute the area of intersection rectangle
    # interArea = max(0, abs(xB - xA) + 1) * max(0, abs(yB - yA) + 1) 
    interArea = abs((xB - xA) * (yB - yA)) # improved measure

    # compute the area of both the prediction and ground-truth rectangles
    boxAArea = abs((boxA[2] - boxA[0] + 1) * (boxA[3] - boxA[1] + 1))
    boxBArea = abs((boxB[2] - boxB[0] + 1) * (boxB[3] - boxB[1] + 1))

    # compute the intersection over union by taking the intersection
    # area and dividing it by the sum of prediction + ground-truth
    # areas - the interesection area
    iou = abs(interArea / float(boxAArea + boxBArea - interArea))

    return iou


def helper_edges(original):
    '''
    Ensemble of binary and canny method to detect clean spiculation border
    to do: used in hough
    Returns edges
    '''
    orig = original.pixel_array

    thresh = threshold_mean(orig) # binarise image
    binary = orig > thresh
    edges = canny(binary, sigma=5)

    return edges

def generate_hough(original):
    '''
    Active contour model
        Define segmented mask proportional to the target mass region 
    Returns number of lines
    ''' 
    orig = original.pixel_array
    lines = []
    edges = helper_edges(original)  # get edges from canny
    tested_angles = np.linspace(-np.pi / 2, np.pi / 2, 100) # permute over angles
    h, theta, d = hough_line(edges, theta=tested_angles)


    origin = np.array((0, orig.shape[1]))
    for _, angle, dist in zip(*hough_line_peaks(h, theta, d)):
        y0, y1 = (dist - origin * np.cos(angle)) / np.sin(angle)
        inter_lines = abs(y0-y1) 
        lines.append(inter_lines)
    num_lines = len(lines)
    return num_lines


def generate_snake(original):
    '''
    Active contour model
        Define segmented mask proportional to the target mass region 
    returns rugged mean dist from defined centroid at r,c
    ''' 
    orig = original.pixel_array

    # spic_area = round(0.01*orig.size)
    spic_area = 100

    s = np.linspace(0, 2*np.pi, spic_area)
    r = 200 + 100*np.sin(s)
    c = 220 + 100*np.cos(s)
    init = np.array([r, c]).T
    snake = active_contour(gaussian(orig, 3),
                             init, alpha=0.015, beta=10, gamma=0.001)

    snake_array = np.asarray(snake)
    dist = np.sqrt((r-snake_array[:, 0])**2 +(c-snake_array[:, 1])**2)
    mean_dist = int(np.mean(dist))
    return mean_dist


def generate_gabor(original):
    '''
    Gabor features
    '''    
    orig = original.pixel_array
    kernels = []
    for theta in range(4):
        theta = theta / 4. * np.pi
        for sigma in (1, 3):
            for frequency in (0.05, 0.25):
                kernel = np.real(gabor_kernel(frequency, theta=theta,
                                              sigma_x=sigma, sigma_y=sigma))
                kernels.append(kernel)

    feats = np.zeros((len(kernels), 2), dtype=np.double)
    for k, kernel in enumerate(kernels):
        filtered = ndimage.convolve(orig, kernel, mode='wrap')
        feats[k, 0] = filtered.mean()
        feats[k, 1] = filtered.var()
    return len(feats)



def make_all_features(original, filled):
    '''
    Runs all manual feature generation features on image
    Takes: original image (dicom) and region mask pixel array
    Returns: single row of data frame with features computed
    '''
    
    orig = original.pixel_array
    spiculation = compute_spiculation(orig, filled)

    # try computing spiculation on a rescaled version of the image
    p_thresh, p100 = np.percentile(orig, (50, 100))
    img_scaled = exposure.rescale_intensity(orig, in_range=(p_thresh, p100))
    spiculation_rescaled = compute_spiculation(img_scaled, filled)
    circularity = compute_circularity(filled)
    # Parth's features
    iou = generate_iou(original, filled)
    hough = generate_hough(original)
    snake = generate_snake(original)
    gabor = generate_gabor(original)

    mf = {'spiculationA': spiculation['A'], \
         'spiculationB': spiculation['B'], \
         'spiculationC': spiculation['C'], \
         'spiculationD': spiculation['D'], \
         'spiculationRA': spiculation_rescaled['B'], \
         'spiculationRB': spiculation_rescaled['B'], \
         'spiculationRC': spiculation_rescaled['C'], \
         'spiculationRD': spiculation_rescaled['D'],
         'circularity': circularity, \
         'iou': iou, \
         'hough': hough, \
         'snake': snake, \
         'gabor': gabor}
    
    return mf


if __name__ == "__main__":
    
    benign_path = "raw/Mass-Training_P_00187_LEFT_CC_1-07-21-2016-DDSM-85364-1-ROI_mask_images-25005-000000.dcm"
    malignant_path = "raw/Mass-Training_P_00149_LEFT_CC_1-07-21-2016-DDSM-06526-1-ROI_mask_images-57657-000001.dcm"

    # read in a test image to play with
    benign, orig_benign = p.go(benign_path)
    malignant, orig_malignant = p.go(malignant_path)

    # plt.imshow(orig_benign.pixel_array)
    # plt.show()
    # plt.imshow(orig_malignant.pixel_array)
    # plt.show()

    # b_thetas, b_magnitudes = compute_sobel(orig_benign.pixel_array, benign)
    # m_thetas, m_magnitudes = compute_sobel(orig_malignant.pixel_array, malignant)

    # print(compute_spiculation(orig_benign, benign))
    # print(compute_spiculation(orig_malignant, malignant))

    # make_all_features(orig_malignant, malignant)

    # I don't know how to interpret the results of this
    # hough_trans = hough_line(filled_img)













