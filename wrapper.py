import logging
import json
import requests
from collections import OrderedDict
SHOP = 'shop'
DM_MARKET = 'dmshop'
SHELF_FLOOR = '{}:\'ShelfLayer\''.format(SHOP)
SHELF_SYSTEM = '{}:\'DMShelfFrame\''.format(DM_MARKET)
MAX_SOLUTION_COUNT = 1000000  # 1.000.000
URL="http://localhost:62226"

class KnowRobREST(object):
    logger = logging.getLogger("KnowRob")
    logger.setLevel(logging.INFO)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    # create formatter and add it to the handlers
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(ch)

    def get_all_individuals_of(self, object_type):
        # q = ' findall(R, rdfs_individual_of(R, {}), Rs).'.format(object_type)
        q = ' findall(R, instance_of(R, {}), Rs).'.format(object_type)
        response=self.once(q) #Find all give all answers in one go and one repose frame
        instances=[]
        for instance in response["Rs"]:
            instances.append(instance)
        self.logger.info(instances)
        return instances
        # solutions = self.once(q)['Rs']
        # return [self.remove_quotes(solution) for solution in solutions]

    def all_solutions(self,q,maxSoulution=MAX_SOLUTION_COUNT):
        jsondict={}
        jsondict["query"]=q
        jsondict["maxSolutionCount"]=maxSoulution
        endpoint=URL+"/knowrob/api/v1.0/query"
        self.logger.info("{} Query: {}".format(endpoint,json.dumps(jsondict)))
        response=requests.post(endpoint,data=json.dumps(jsondict),headers={'Content-Type': 'application/json'})
        return json.loads(response.content)["response"]

    def once(self,q):
        return self.all_solutions(q)[0]

    def get_object_frame_id(self, object_id):
        """
        :type object_id: str
        :return: frame_id of the center of mesh.
        :rtype: str
        """
        q = 'holds(\'{}\', knowrob:frameName, R).'.format(object_id)
        response=self.all_solutions(q)
        return response[0]['R']

    def get_object_pose(self,object_id,frame='map'):
        q = "is_at('{}' , ['{}', Translaiton, Quaternion])".format(object_id,frame)
        response=self.once(q)
        return response # {'Pose': ['map', [1.76438074478, -1.4001872933, 0.8], [0.0, 0.0, 0.999786808849, 0.0206479260808]]}

    def get_shelf_layer_from_system(self, shelf_system_id):
        """
        :type shelf_system_id: str
        :return: returns dict mapping floor id to pose ordered from lowest to highest
        :rtype: dict
        """
        q = 'triple(\'{}\', dul:hasComponent, Floor), ' \
            'instance_of(Floor, {}), ' \
            'object_feature_type(Floor, Feature, dmshop:\'DMShelfPerceptionFeature\'),' \
            'holds(Feature, knowrob:frameName, FeatureFrame).'.format(shelf_system_id, SHELF_FLOOR)
        response=self.all_solutions(q)
        floors={}
        ssets=set()
        for solution in response:
            if(solution['Floor'] in ssets): # ToDo: Fix this the query is wrong but I dont want to annoy Kaviya again
                pass
            else:
                ssets.add(solution['Floor'] )
                floor_id=solution['Floor']
                floor_pose=self.get_object_pose(floor_id)
                floors[floor_id]=floor_pose
        floor=floors.items()
        # for item in floor:
        #     print(item[1]['Translaiton'][2])
        floor=list(sorted(floor, key=lambda x: x[1]['Translaiton'][2]))  #item[1]['Pose'][1][2] --> Pose.Z
        floors=OrderedDict(floor)
        return floors

    def get_shelf_system_from_layer(self, shelf_layer_id):
        """
        :type shelf_layer_id: str
        :rtype: str
        """
        q = 'shelf_layer_frame(\'{}\', Frame).'.format(shelf_layer_id)
        shelf_system_id = self.once(q)['Frame']

        return shelf_system_id

    def get_facing_ids_from_layer(self, shelf_layer_id):
        """
        :type shelf_layer_id: str
        :return:
        :rtype: OrderedDict
        """
        shelf_system_id = self.get_shelf_system_from_layer(shelf_layer_id)
        q = 'findall([F, P], (shelf_facing(\'{}\', F),is_at(F, P)), Fs).'.format(shelf_layer_id) # ToDo: Fix Query (Worng Poseframe)
        solutions = self.all_solutions(q)[0]
        facings = []
        for facing_id, pose in solutions['Fs']:
            facing_pose = pose
            # facing_pose = transform_pose(self.get_perceived_frame_id(shelf_layer_id), facing_pose)
            facings.append((facing_id, facing_pose))
        # try: What is is_left?
        #     is_left = 1 if self.is_left(shelf_system_id) else -1
        # except TypeError:
        #     is_left = 1
        # facings = list(sorted(facings, key=lambda x: x[1].pose.position.x * is_left))

        return OrderedDict(facings)

    def get_products_in_facing(self, facing_id):
        q = 'triple(\'{}\', shop:productInFacing, Obj).'.format(facing_id)
        solutions = self.all_solutions(q)
        products = []
        for binding in solutions:
            products.append(binding['Obj'])
        return products

    def get_object_dimensions(self, object_class):
        """
        :param object_class:
        :return: [x length/depth, y length/width, z length/height]
        """
        q = 'object_dimensions(\'{}\', X_num, Y_num, Z_num).'.format(object_class)
        solutions = self.once(q)
        if solutions:
            return [solutions['Y_num'], solutions['X_num'], solutions['Z_num']]

knowrob=KnowRobREST()

ids=knowrob.get_all_individuals_of(SHELF_SYSTEM)
layerids=knowrob.get_shelf_layer_from_system(ids[0])
rng_layer_id=next(iter(layerids))
facings=knowrob.get_facing_ids_from_layer(rng_layer_id)
rng_facing_id=next(iter(facings))
print(rng_facing_id)
itemids=knowrob.get_products_in_facing(rng_facing_id)
print(knowrob.get_object_dimensions(itemids[0]))

