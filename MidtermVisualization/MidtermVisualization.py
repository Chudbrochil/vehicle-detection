from StereoDepth import Convert3D
import numpy as np
import os
import matplotlib.pyplot as plt
from onlinekalman import MultiOnlineKalman
from mpl_toolkits.mplot3d import Axes3D
import cv2
import open3d as o3d
import copy

#
# To use: Just run python 'MidtermVisualization.py'
#
#
# To change camera angle: Run 'python ChangeVisualizationViewpoint.py', move the camera
# around until it's where you want, then press q. Then run 'MidtermVisualization.py'
#
#



current_directory = os.getcwd()
info = np.load(current_directory + '/../0010-left-info.pyc', allow_pickle=True)
directory_l = current_directory + '/../data_tracking_image_2/training/image_02/0010/'
directory_r = current_directory + '/../data_tracking_image_2/training/image_03/0010/'


vis = o3d.visualization.Visualizer()
pcd = o3d.geometry.PointCloud()
vis.create_window()

opt = vis.get_render_option()
opt.background_color = np.asarray([0, 0, 0]) # set background to black
opt.point_size = 5
opt.line_width = 100    # doesn't seem to be working


max_files = 100 # run on first 100 frames
line_sets = [] # 3D bounding boxes


kalman = MultiOnlineKalman()

fig, ax = plt.subplots()
im = ax.imshow(cv2.imread(os.path.join(directory_l, '000000.png')))

no_kalman_out_file = open('nokalmanbbox.txt', 'w')
kalman_out_file = open('kalmanbbox.txt', 'w')
for i, filename in enumerate(sorted(os.listdir(directory_l))):
    if i > max_files:
        break

    if filename.endswith('.png'):
        filename_l = os.path.join(directory_l, filename)
        filename_r = os.path.join(directory_r, filename)

        # clear old bounding boxes --------
        for line_set in line_sets:
            vis.remove_geometry(line_set)
        # clear old bounding boxes --------


        # Use StereoDepth Conversions---------------------------------
        frame = Convert3D(filename_l, filename_r, info[i])
        # add point cloud
        pcd.points = o3d.utility.Vector3dVector(np.int16(frame.point_cloud * 10))

        #print(frame.point_cloud.shape[0])
        #image_colors_depth = np.full((frame.point_cloud.shape[0], 3), 100.)
        image_colors_depth = frame.point_cloud
        image_colors_depth[:,0] = image_colors_depth[:,2]/50 %1
        image_colors_depth[:,1] = image_colors_depth[:,2]/25 %1
        image_colors_depth[:,2] = image_colors_depth[:,2]/12 %1
        #image_colors_depth[:,2] = 0.5
        #print(image_colors_depth)
        #exit(0)
        '''
        for point_index in range(0, frame.point_cloud.shape[0]):
            point_x = frame.point_cloud[point_index][0]
            point_y = frame.point_cloud[point_index][1]
            point_z = frame.point_cloud[point_index][2]
            x_color = point_x*1000 % 1.0
            y_color = point_y*1000 % 1.0
            z_color = point_z % 1.0
            image_colors_depth[point_index][0] = x_color
            image_colors_depth[point_index][1] = y_color
            image_colors_depth[point_index][2] = z_color
        '''

        #print(image_colors_depth.shape)
        #print(image_colors_depth)
        #exit(0)
        pcd.colors = o3d.utility.Vector3dVector(np.float64(image_colors_depth))
        # Use StereoDepth Conversions---------------------------------

        if i == 0:
            vis.add_geometry(pcd)


        # add bounding boxes-------------------------------------------
        for pos in kalman.take_multiple_observations(frame.positions_3D): #frame.positions_3D is a list of positions (multiple if we detect more than one car in the same frame)
            # pos is a list of xyz, e.g. [0.45 3.10 5.0]
            print(pos)
            print("----------------")
            #exit(0)
            #pos = kalman.take_multiple_observations(pos)
            
            points = [[-10, -10, -10], [10, -10, -10], [-10, 10, -10], [10, 10, -10], [-10, -10, 10], [10, -10, 10],
                      [-10, 10, 10], [10, 10, 10]]
            points = (np.int16(points) + np.int16(np.array(pos)*10)).tolist()
            kalman_out_file.write("{}\n".format(points))
            lines = [[0, 1], [0, 2], [1, 3], [2, 3], [4, 5], [4, 6], [5, 7], [6, 7],
                     [0, 4], [1, 5], [2, 6], [3, 7]]

            colors = [[0, 1, 0] for i in range(len(lines))] # set bounding box color to green
            line_set = o3d.geometry.LineSet()
            line_set.points = o3d.utility.Vector3dVector(points)
            line_set.lines = o3d.utility.Vector2iVector(lines)
            line_set.colors = o3d.utility.Vector3dVector(colors)
            vis.add_geometry(line_set) # add bounding box to visualizer
            line_sets.append(line_set) # add it to line_sets so we can clear it at the next iteration
        for pos in frame.positions_3D: #frame.positions_3D is a list of positions (multiple if we detect more than one car in the same frame)
            # pos is a list of xyz, e.g. [0.45 3.10 5.0]
            print(pos)
            print("----------------")
            #exit(0)
            #pos = kalman.take_multiple_observations(pos)
            
            points = [[-10, -10, -10], [10, -10, -10], [-10, 10, -10], [10, 10, -10], [-10, -10, 10], [10, -10, 10],
                      [-10, 10, 10], [10, 10, 10]]
            points = (np.int16(points) + np.int16(np.array(pos)*10)).tolist()
            no_kalman_out_file.write("{}\n".format(points))
            
            lines = [[0, 1], [0, 2], [1, 3], [2, 3], [4, 5], [4, 6], [5, 7], [6, 7],
                     [0, 4], [1, 5], [2, 6], [3, 7]]

            colors = [[0, 0, 1] for i in range(len(lines))] # set bounding box color to blue
            line_set = o3d.geometry.LineSet()
            line_set.points = o3d.utility.Vector3dVector(points)
            line_set.lines = o3d.utility.Vector2iVector(lines)
            line_set.colors = o3d.utility.Vector3dVector(colors)
            vis.add_geometry(line_set) # add bounding box to visualizer
            line_sets.append(line_set) # add it to line_sets so we can clear it at the next iteration
        # add bounding boxes-------------------------------------------


        # Change Camera Position --------------------------------------
        ctr = vis.get_view_control() # load viewpoint
        param = o3d.io.read_pinhole_camera_parameters(current_directory + '/viewpoint.json')
        ctr.convert_from_pinhole_camera_parameters(param)
        # Change Camera Position --------------------------------------


        vis.poll_events()
        vis.update_renderer()
        vis.update_geometry()

        print(i)

        # Draw 2D image with 2D bounding boxes for debugging -------------------
        left_image = cv2.imread(filename_l)
        for bound in info[i]:
            if bound[4] == 'car' and float(bound[5]) > 0.9:
                cv2.rectangle(left_image, (int(bound[2]), int(bound[0])), (int(bound[3]), int(bound[1])), (255, 0, 0), 2)
        #plt.imshow(left_image, vmin=-1, vmax = 50)
        im.set_data(left_image)
        plt.pause(0.1)
        plt.draw()
        # Draw 2D image with 2D bounding boxes for debugging -------------------
