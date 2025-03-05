import cv2
import pandas as pd
import numpy as np
from ultralytics import YOLO
import pickle
from multiprocessing import Queue
from multiprocessing import Manager
import threading
from sqlalchemy import create_engine, Column, Integer, Boolean , String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import json

# Define the database connection
engine = create_engine('mysql+pymysql://root:@localhost/parkeasy', echo=True)  # Use your database connection details

# Define a base class for declarative class definitions
# Base = declarative_base()

# Define a class representing the parking slot table
# class slotStatus(Base):
#     __tablename__ = 'slotStatus'

#     slot = Column(Integer, primary_key=True, nullable = False , unique = True, )
#     status = Column(String, primary_key=False)

# Create the tables in the database
# Base.metadata.create_all(engine)

# Create a session to interact with the database
Session = sessionmaker(bind=engine)
session = Session()


"""Colors"""
blue = (255,0,0)
green = (0, 255, 0)
white = (255,255,255)
red = (0,0,255)
orange = (0, 165, 255)
"""File Reading Sections"""
# Models , classes and coordinates
pickleFile = r'coordinate'
pointsFile = r'slot_number'
class_file = r'models\main\class.txt'
model_file = r'models\main\best.pt'
vid_path = r'data\Fully_parked.mp4'
# vid_path = r'data\2 legal  1 parking + outgoing 1 illegal_part2.mp4'
# vid_path = r'data\red_car_illegal_stop.mp4'
vid_path = r'data\partially_parked_extended.mp4'
vid_path = r'data\main.mp4'
# vid_path = r'data\bus.MOV'
dist_file = r'distances.json'
slot_status = r'slot_status.json'
imgPath = r'empty.jpg'
model=YOLO(model_file)
classes = open(class_file, "r")
classes = classes.read()
classes = classes.split("\n")
file_path = "slot_status.txt"

try:
    with open(pickleFile , 'rb') as f:
        poslist = pickle.load(f)
except:
    poslist = []

try:
    with open(pointsFile, 'rb') as f:
        points = pickle.load(f)
except:
    points = []



"""Constants"""
K = 0   # Callibration Factor for disntance
focal_length = 1472  # Focal length in pixels (this value needs to be determined/calibrated)
object_height = 142     # Actual width of the object in meters
distance = "Null"
frame_skip_count = 0
count = 0


def calculate_distance(object_height, focal_length, apparent_height):
    distance = (object_height * focal_length) 
    distance = distance / apparent_height
    return distance


def process(q, q2, stop_event, slot_statuses):
    global distances
    cap=cv2.VideoCapture(vid_path)
    frame_skip_count = 0

    while not stop_event.is_set():
        slot_statuses.update({slot_number: "Empty" for slot_number in range(1, len(poslist) + 1)})
        ret,frame = cap.read()
        if not ret:
            break
        
        frame_skip_count += 1
        if frame_skip_count < 10:  
            continue
        else:
            frame_skip_count = 0

        frame=cv2.resize(frame,(1020,772))
        h , w , _ = frame.shape
        frame = frame[250 : h ,500:w-170]
        frame2 = cv2.imread(imgPath)
        frame2=cv2.resize(frame2,(1020,772))
        frame2 = frame2[250 : h ,500:w-170]
        
        results=model.predict(frame)
        a = results
        a=a[0].boxes.data
        px=pd.DataFrame(a).astype("float")
        count = 0
        distances = {}
        areas = []
        
        for area_number , area in enumerate(poslist):
            cv2.polylines(frame2,[np.array(area,np.int32)],True,orange,2)
            for index ,row in px.iterrows():
                x1=int(row[0])
                y1=int(row[1])
                x2=int(row[2])
                y2=int(row[3])
                d=int(row[5])
                c=classes[d]

                if 'car' in c:
                    W=int(x2 - x1)
                    H=int(y2 - y1)

                    apparent_height = H  
                    distance_calculated = calculate_distance(object_height, focal_length, apparent_height)
                    distance = distance_calculated - K 
                    
                    if distance < 1500:
                        cv2.rectangle(frame, (x1, y1), (x2, y2), red, 2)
                        # cv2.rectangle(frame2, (x1, y1), (x2, y2), red, 2)
                        continue

                    area_P = ((x1 , y1 ),(x2 , y1) ,(x2 , y2) , (x1 , y2) )
                    xy_i = area[0]
                    xy_f = area[2]
                    cx = int((xy_f[0] + xy_i[0])/2)
                    cy = int((xy_f[1] + xy_i[1])/2)
                    PolyGoneTest=cv2.pointPolygonTest(np.array(area_P,np.int32),((cx,cy)),False)
                    cv2.rectangle(frame,(x1,y1),(x2,y2),white,2)
                    if PolyGoneTest>=0:
                        slot_statuses[area_number + 1] = "Filled"
                        distances[(area_number+1)] = distance 
                        count = count + 1
                        cv2.circle(frame,(cx,cy),3,blue,-1)
                        cv2.polylines(frame,[np.array(area,np.int32)],True,red,2)
                        areas.append((area_P ,area_number , area ))
                    else:
                        cv2.polylines(frame,[np.array(area,np.int32)],True,green,2)  
                    
                elif 'bus' in c or 'truck' in c or 'motorcycle' in c:
                    W=int(x2 - x1)
                    H=int(y2 - y1)

                    apparent_height = H  
                    distance_calculated = calculate_distance(object_height, focal_length, apparent_height)
                    distance = distance_calculated - K 
                    
                    if distance < 1500:
                        area_P = ((x1 , y1 ),(x2 , y1) ,(x2 , y2) , (x1 , y2) )
                        cv2.polylines(frame,[np.array(area_P,np.int32)],True,red,2)          
        cv2.putText(frame,f"Available: {len(poslist) - count}",(23,300),cv2.FONT_HERSHEY_PLAIN,3,(0,255,0),2)
        print(f"dict : {dict(slot_statuses)}")
        for slot, status in slot_statuses.items():
            print(f"slot: {slot}")
            print(f"status: {status}")
            # existing_slot = session.query(slotStatus).filter_by(slot=slot).first()
            # print(f"existing_slot.status : {existing_slot.status}")
            
            # if existing_slot:
            #     # If the slot exists, update its status
            #     existing_slot.status = status
            #     # new_slot = slotStatus(slot=slot, status=status)
            #     # session.add(new_slot)
            #     #session.commit()
            # else:
            #     # If the slot does not exist, create a new record
            #     # new_slot = slotStatus(slot=slot, status=status)
            #     # session.add(new_slot)
            #     # session.commit()
        # session.close()
        
        for area_number , point in enumerate(points):
            cv2.putText(frame,f"{area_number+1}",point,cv2.FONT_HERSHEY_COMPLEX_SMALL,1,green,2)
            cv2.putText(frame2,f"{area_number+1}",point,cv2.FONT_HERSHEY_COMPLEX_SMALL,1,orange,2)
        
        q.put(frame)
        q2.put(frame2)
        
        with open("parking_spaces.txt", "w") as file:
            for area_tuple in areas:
                file.write(f"{area_tuple}\n")

        with open(file_path, 'w') as file:
            json.dump(dict(slot_statuses), file)
        
        if cv2.waitKey(1)&0xFF==27:
            # cv2.imwrite("userImg.jpeg" , frame2)
            with open(dist_file, 'w') as file:
                json.dump(distances, file)
            with open(slot_status, 'w') as file:
                json.dump(dict(slot_statuses), file)
            cap.release()
            cv2.destroyAllWindows()
            stop_event.set()  
        

def Display(q , q2 , stop_event, slot_statuses):
    while not stop_event.is_set():
        if q.empty() != True:
            frame = q.get()
            cv2.imshow("Manager Feed", frame)
            
        if q2.empty() != True:
            frame2 = q2.get()
            cv2.imshow("User Feed" , frame2)

        if cv2.waitKey(1) & 0xFF == 27:
            # cv2.imwrite("userImg.jpeg" , frame2)
            with open(dist_file, 'w') as file:
                json.dump(distances, file)
            with open(slot_status, 'w') as file:
                json.dump(dict(slot_statuses), file)
            cv2.destroyAllWindows()
            stop_event.set()

if __name__ == '__main__':
    q = Queue()
    q2 = Queue()
    stop_event = threading.Event()
    manager = Manager()
    
    
    slot_statuses = manager.dict({slot_number: "Empty" for slot_number in range(1, len(poslist) + 1)})
    p1 = threading.Thread(target=process, args=(q, q2, stop_event, slot_statuses))
    p3 = threading.Thread(target=Display, args=(q,q2 , stop_event, slot_statuses))

    p1.start()
    p3.start()

    p1.join()
    p3.join()
