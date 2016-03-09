import sys
import simpy
import numpy
import math
import queue
from numpy.random import exponential
from numpy import mean
from heapq import heappush, heappop, heapify
from random import randint


# Globals
X_MEAN_PARKING = 5.0
PARKING_CAP = .10
SCALE = 70/500
CAR_SIZE = 15 * SCALE
POLICE = False
exit_count = 0
# Event parameters
MEAN_TRAVEL_TIME = 5.0 # minutes
MEAN_WAITING_TIME = 2.0 # minutes
globalTimeList = []
currentRoadCapacities = {}
exit_list = [(-1,-1), (-1,-1), (-1,-1)]
"""
Method to read from the world file and create a basic graph dictionary to pull
from for creating intersection and parking lot nodes.  There are no one lane
roads in this model except from exiting a parking lot.
fileName - name of file to read from
Return - return intersection dictionary of nodes and incoming queues to node
with capacities for each queue (number of lanes) and
parking lots dictionary of nodes with capacties of each.
Intersection Format -  (89, 81): [((86, 129),1), ((50, 87),2)]
Parking Lot Format  -  (86, 149): 1200
"""
def readFileAndSetUp(fileName):
    worldFile = open(fileName,'r')
    worldFile.readline() # Throw Away top line

    intersections_graph = {}
    parking_nodes = {}

    for line in worldFile:
        array = line.split(',')
        typeNode = array[0]
        nodeFrom = (int(array[1]),int(array[2]))
        nodeTo = (int(array[3]),int(array[4]))
        capacity = int(array[5])

        # Street Nodes; lets process these
        if typeNode == 'Street':
            # Add queue for NodeTo to NodeFrom
            if nodeFrom not in intersections_graph:
                intersections_graph[nodeFrom] = []
                intersections_graph[nodeFrom].append((nodeTo,capacity))
            else:
                intersections_graph[nodeFrom].append((nodeTo,capacity))
            # Add queue for NodeFrom to NodeTo
            if nodeTo not in intersections_graph:
                intersections_graph[nodeTo] = []
                intersections_graph[nodeTo].append((nodeFrom,capacity))
            else:
                intersections_graph[nodeTo].append((nodeFrom,capacity))


        # Parking Nodes; lets process these; never allowing a queue to enter
        # parking lot; use one as a capacity holder for roads coming from
        # parking lot
        elif typeNode == 'Parking':
            if nodeFrom not in intersections_graph:
                intersections_graph[nodeFrom] = []
                intersections_graph[nodeFrom].append((nodeTo,1))
            # Shouldn't ever happen, since there is only one parking lot per
            # coordinate, but let's check anyways
            else:
                intersections_graph[nodeFrom].append((nodeTo, 1))

            parking_nodes[nodeFrom] = (capacity) #, nodeTo)

    worldFile.close()

    #for item in sorted(intersections_graph):
    #    print (item, intersections_graph[item])

    return intersections_graph, parking_nodes

"""
Method to create dictionary of current and maximum capacities for each queuing
road segment upto a particular intersection.  The dictionary can be accessed by
asking from the dictionary what intersection of queues you want.
intersections - dictionary of intersections for the entire map system
Return - return intersection dictionary of upstream nodes with current and max
queue size.
Intersection Format - (348, 30): [((168, 30), 0, 171), ((380, 35), 0, 30)]
"""
def createQueuingCapacityDict(intersections):
    global currentRoadCapacities

    # Go through each intersection node in the intersection dictionary
    for intersectionNode in intersections:
        currentRoadCapacities[intersectionNode] = []
        # Go through each downstream node and add capacity
        for downstreamNode, numLanes in intersections[intersectionNode]:
            currentRoadCapacities[intersectionNode].append((downstreamNode,
            calculateRoadCapacity(intersectionNode, downstreamNode, numLanes)))

    return currentRoadCapacities





# Create the global queue of car tuples
def globalQueue(parkingDicts):
    for key in parkingDicts:
        #print(key, parkingDicts[key][0])
        X_COUNT = parkingDicts[key][0]
        x_values = exponential (X_MEAN_PARKING, X_COUNT)
        #print("X ~ Exp(%g):" % X_MEAN)
        #for (i, x_i) in enumerate (x_values):
            #print ("  X_%d = %g" % (i, x_i))
        listOfTimeStamps = list(x_values)
        for time in listOfTimeStamps:
            carTuple = (time, key, parkingDicts[key][1], key) #timestamp, from, to, parkinglot
            globalTimeList.append((carTuple, togo))
    heapify(globalTimeList)


now = 0.0 # Current (logical) simulation time

def schedule (car_tuple, event):
    """
    Schedules a new event `e` at time `t`.
    """
    global globalTimeList
    heappush (globalTimeList, (car_tuple, event))

def arrives (car_tuple):
    """
    Processes an arrival event at time `t` for a system in state `s`.
    Schedules a pumping event if the pump is free. Returns the new
    system state.
    """
    # @YOUSE
    t_done = car_tuple[0] + MEAN_TRAVEL_TIME
    car_tuple = (t_done, car_tuple[1], car_tuple[2], car_tuple[3])
    schedule (car_tuple, togo)

def togo (car_tuple):
    "figure out where to go"
    if car_tuple[2] in exit_list:
        global exit_count
        exit_count += 1
    else:
        if POLICE:
            #shortest distance
            values = currentRoadCapacities[car_tuple[1]]
            mini_distance_list = []
            for value in values:
                mini_distance_list.append(math.hypot(car_tuple[1][0] - value[0], car_tuple[1][1] - value[1]))

            shortest_distance = min(mini_distance_list)
            car_tuple = (car_tuple[0], car_tuple[2], shortest_distance, car_tuple[3])

        else:
            # random location
            print(currentRoadCapacities)
            print(car_tuple[1])
            values = currentRoadCapacities[car_tuple[1]]
            random_bound = len(values)
            index = randint(0,random_bound)
            # check for capacity
            car_tuple = (car_tuple[0], car_tuple[2], values[index][0], car_tuple[3])



        if car_tuple[1] != car_tuple[3]: #not in parking lot
            departs(car_tuple[1], car_tuple[2])
        schedule(car_tuple, arrives)


def departs (fromNode, toNode):
    """
    Processes a finished-pumping event at time `t` for a system in
    state `s`. Schedules a pumping event if any cars are waiting.
    Returns the new system state.
    """
    global currentRoadCapacities
    values = currentRoadCapacities[fromNode]
    for value in values:
        if toNode == value[0]:
            value[1] += 1




"""
Method to calculate the capacity for a road between two nodes based on two
end points and number of lanes of road between those two nodes.
firstNode  - firstNode to pull from
secondNode - secondNode to pull from
numLanes   - number of lanes between firstNode and secondNode
Return - return capacity of road between the firstNode and secondNode
"""
def calculateRoadCapacity(firstNode, secondNode, numLanes):
    # Use Euclid distance
    distance = ((firstNode[0] - secondNode[0])**2 +
                (firstNode[1] - secondNode[1])**2)**(0.5)
    numCarsCapacity = (distance * numLanes) // CAR_SIZE

    return int(numCarsCapacity)


def simulate (events):

    # print ("\nFuture event list:\n%s" % str (events))
    # print ("\nt=0: %s" % str (s))

    while events:
        (car_tuple,event) = heappop (events)
        event(car_tuple)

        #print ("t=%d: event '%s' => '%s'" % (t, e.__name__, str (s)))



# More test code: If everything worked, so should this simulation!

def main():
    args = sys.argv

    intersections, parkingLots = readFileAndSetUp(args[1])
    currentRoadCapacities = createQueuingCapacityDict(intersections)



    # Test
    # print (intersections)
    print (currentRoadCapacities)
    # print (parkingLots)
    # print (calculateRoadCapacity((0,0), (10,0), 1))

    #print (intersections)
    #print (parkingLots)
    #print (calculateRoadCapacity((0,0), (10,0), 1))
    globalQueue(parkingLots)
    #print("GLOBAL QUEUE:", sorted(globalTimeList))
    simulate (globalTimeList)
    print(exit_count)
if __name__=='__main__':
	main()






# class ParkingLot(object):
#     def __init__(self, value, percent):
#         self.total = math.ceil(value * percent)
#
#     def cars(self):
#         X_COUNT = self.total
#         x_values = exponential (X_MEAN, X_COUNT)
#         # print ("X ~ Exp(%g):" % X_MEAN)
#         # for (i, x_i) in enumerate (x_values):
#         #     print ("  X_%d = %g" % (i, x_i))
#
#
#
# class Intersection:
#         def __init__(self, key, value, carSize):
#             self.carsPQ = []
#             for x in range (len(value)):
#                 pq = queue.PriorityQueue(maxsize = (math.sqrt((key[0]-value[x][0])**2 + (key[1]-value[x][1])**2) // CAR_SIZE))
#                 self.carsPQ.append(pq)
#
# parkingDict = {}
# intersectionDict = {}
# for key, value in parkingDict:
#     ParkingLot(value, PARKING_CAP)
#
# for key, value in intersectionDict:
#     Intersection(key, value, CAR_SIZE)
