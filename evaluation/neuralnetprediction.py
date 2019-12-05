import sys
import os

#sys.path.append('../darkflow')
#sys.path.append('../visualization')
vd_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.append(vd_directory)
sys.path.append(os.path.join(vd_directory, 'darkflow'))
sys.path.append(os.path.join(vd_directory, 'visualization'))


from darkflow.net.build import TFNet
import cv2
import matplotlib.pyplot as plt
import numpy as np
import pickle
from StereoDepth import *
import visualization2d
from onlinekalman import OnlineKalman, MultiOnlineKalman
from particlefilter import ParticleFilter, MultiOnlineParticleFilter

class NetworkModel:
    def __init__(self):
        self.filt = None
        self.vd_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
        os.chdir(self.vd_directory)
        os.chdir("darkflow")
        options = {"model": os.path.join(self.vd_directory, "network/cfg/kitti.cfg"),
                   "load": -1,
                   "threshold": 0.01,
                   "gpu": 0.8}

        self.tfnet = TFNet(options)

    def PredictFrame(self, sequence_name, image_name, filter_type='kalman', add_old_detections=True, filter_high_confidence_only=False):
        #print("----------------------")
        #directory_l = os.path.join(self.vd_directory, "data/KITTI-tracking/training/image_02/", sequence_name)
        #directory_r = os.path.join(self.vd_directory, "data/KITTI-tracking/training/image_03/", sequence_name)
        if type(image_name) == int:
            image_name = str(image_name).zfill(6) + '.png'
        image_path_l = os.path.join(self.vd_directory, "data/KITTI-tracking/training/image_02/", sequence_name, image_name)
        image_path_r = os.path.join(self.vd_directory, "data/KITTI-tracking/training/image_03/", sequence_name, image_name)

        bgr_image = cv2.imread(image_path_l)
        rgb_image = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
        yolo_prediction = self.tfnet.return_predict(rgb_image)
        stereoPrediction = Convert3D(image_path_l, image_path_r, yolo_prediction)

        frame_data = {'tracked_objects': [], 'image_l': rgb_image, 'image_depth': stereoPrediction.depth_img, 'point_cloud': stereoPrediction.point_cloud}

        raw_object_3d_positions = []
        raw_confidences = []
        high_confidence_indexes = []

        index = 0
        for predicted_box, predicted_3d_position in zip(yolo_prediction, stereoPrediction.positions_3D):
            if predicted_box['confidence'] > 0.8 or not filter_high_confidence_only:
                raw_object_3d_positions.append(list(predicted_3d_position))
                raw_confidences.append(predicted_box['confidence'])
                high_confidence_indexes.append(index)
            index += 1

        if filter_type == 'kalman':
            if self.filt is None or self.filt.sequence_name != sequence_name:
                self.filt = MultiOnlineKalman(sequence_name)
            filtered_object_3d_positions, confidences = self.filt.take_multiple_observations(raw_object_3d_positions, raw_confidences)
        elif filter_type == 'particle':
            if self.filt is None or self.filt.sequence_name != sequence_name:
                self.filt = MultiOnlineParticleFilter(sequence_name)
            filtered_object_3d_positions, confidences = self.filt.take_multiple_observations(raw_object_3d_positions, raw_confidences)

        index = 0
        filtered_positions_index = 0
        for predicted_box, predicted_3d_position in zip(yolo_prediction, stereoPrediction.positions_3D):
            tracked_object = {}
            tracked_object['bbox'] = {'left': predicted_box['topleft']['x'], 'top': predicted_box['topleft']['y'], 'right': predicted_box['bottomright']['x'], 'bottom': predicted_box['bottomright']['y']}
            tracked_object['confidence'] = predicted_box['confidence']
            tracked_object['type'] = predicted_box['label']
            if filter_type is not None and (not filter_high_confidence_only or index in high_confidence_indexes):
                tracked_object['3dbbox_loc'] = filtered_object_3d_positions[filtered_positions_index]
                filtered_positions_index += 1
            else:
                tracked_object['3dbbox_loc'] = predicted_3d_position
            raw_object_3d_positions.append(list(predicted_3d_position))
            frame_data['tracked_objects'].append(tracked_object)
            if predicted_box['confidence'] > 0.8:
                pass
                #print(predicted_3d_position)
            index += 1

        if filter_type is not None and add_old_detections:
            while filtered_positions_index < len(filtered_object_3d_positions):
                tracked_object = {}
                tracked_object['bbox'] = {'left': 0, 'top': 0, 'right': 0, 'bottom': 0}
                tracked_object['confidence'] = confidences[filtered_positions_index]
                tracked_object['type'] = 'Car_0'
                tracked_object['3dbbox_loc'] = filtered_object_3d_positions[filtered_positions_index]
                if confidences[filtered_positions_index] > 0:
                    #print("Added old  detection")
                    frame_data['tracked_objects'].append(tracked_object)
                filtered_positions_index += 1





        #print("Number of objects: {}; Number of filters:{}".format(len(raw_object_3d_positions), len(self.kalmanfilter.filter_list)))


        return frame_data


    def PredictSequence(self, sequence_name = '0010', visualize=False):
        directory_l = os.path.join(self.vd_directory, "data/KITTI-tracking/training/image_02/", sequence_name)
        directory_r = os.path.join(self.vd_directory, "data/KITTI-tracking/training/image_03/", sequence_name)

        out_directory = os.path.join(self.vd_directory, 'eval', sequence_name, 'predictions')
        os.makedirs(out_directory, exist_ok=True)
        # Iterate over images

        _, ax = plt.subplots(figsize=(20, 10))
        im = None

        for i, filename in enumerate(sorted(os.listdir(directory_l))):
            if filename.endswith('.png'):
                print("Sequence: ", sequence_name, "  ", i, "/", len(os.listdir(directory_l)), end='\r', flush=True)
                frame_data = self.PredictFrame(sequence_name, filename)
                out_file_name = os.path.join(out_directory, os.path.splitext(filename)[0])

                if visualize:
                    img = visualization2d.Draw2DBoxes(frame_data)
                    if not im:
                        im = ax.imshow(img)
                    else:
                        im.set_data(img)
                    plt.pause(0.01)
                    plt.draw()

                with open(out_file_name, 'wb+') as out_file:
                    pickle.dump(frame_data, out_file, pickle.HIGHEST_PROTOCOL)
        plt.close()


"""
# DEPRECATED #
def OutPrediction(prediction, frame_number, out_directory, image_l_path, image_r_path):
    # Save prediction as a file.
    os.makedirs(out_directory, exist_ok=True)
    out_file_name = os.path.join(out_directory, str(frame_number).zfill(4))
    stereoPrediction = Convert3D(image_l_path, image_r_path, prediction)
    with open(out_file_name, 'wb+') as out_file:
        frame = []
        for predicted_box, predicted_3d_position in zip(prediction, stereoPrediction.positions_3D):
            tracked_object = {}
            tracked_object['bbox'] = {'left': predicted_box['topleft']['x'], 'top': predicted_box['topleft']['y'], 'right': predicted_box['bottomright']['x'], 'bottom': predicted_box['bottomright']['y']}
            tracked_object['confidence'] = predicted_box['confidence']
            tracked_object['type'] = predicted_box['label']
            tracked_object['3dbbox_loc'] = predicted_3d_position
            frame.append(tracked_object)

        pickle.dump(frame, out_file, pickle.HIGHEST_PROTOCOL)
"""
