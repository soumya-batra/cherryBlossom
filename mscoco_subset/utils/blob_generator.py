import os
import base64
import glob
import datetime
import json
import uuid
import exifread
import urllib.request
import certifi
import json
import ast

from detected_object_unpacker import *

# Helper class for geo-encoding and reverse geo-encoding 
class GeoEnodingHelper:
    def __init__(self):
        self.GEO_API_KEY = "AIzaSyBDvkEwnaH_ePorXvJOlnCTk1smpmIwBmk"
        self.endpoint = "https://maps.googleapis.com/maps/api/geocode/json?key=AIzaSyBDvkEwnaH_ePorXvJOlnCTk1smpmIwBmk&latlng="

    def dms_to_dd(self, d, m):
        dd = d + float(m)/60
        return dd

    def get_address(self, lat, lon):
        if len(lat.strip())==0 or len(lon.strip())==0:
            return ""

        lat = str(lat).split(",")[:2]
        lat = ",".join(lat)[1:]

        lon = str(lon).split(",")[:2]
        lon = ",".join(lon)[1:]
        
        lat = [int(x) for x in str(lat).split(",")]
        lon = [int(x) for x in str(lon).split(",")]

        lat_d = self.dms_to_dd(lat[0], lat[1])
        lon_d = self.dms_to_dd(lon[0], lon[1])

        _url = self.endpoint + str(lat_d)+ ",-" + str(lon_d)
        contents = urllib.request.urlopen(_url, cafile=certifi.where()).read().decode("utf-8")

        _json = json.loads(contents)
        # print(_json["results"][0]["formatted_address"])

        if "results" in _json:
            if len(_json["results"]) > 0 :
                return _json["results"][0]["formatted_address"]


# Class to generate blob for blob storage to feed in search index
class BlobGenerator:
    def __init__(self):
        self.g = GeoEnodingHelper()
        self.unpacker = DetectedObjectUnpacker()
        self.date = datetime.datetime.now().strftime("%Y%m%d")

    def _get_image_base64(self, img_path):
        with open(img_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read())
            return encoded_string.decode("utf-8") 

    def _get_filename_from_path(self, path):
        if "/" in path:
            return path.split("/")[-1]
        else:
            return path

    def _create_blob(self, fname, pickle_dir, base64img, caption, annotationlist, op_filename, location, datetime, device):
        fname = self._get_filename_from_path(fname)

        entity_names, entity_spatial_metadata = self._get_entities(fname, pickle_dir)
        
        # this is schema for blob storage for azure search index
        _json = {
                    "id" : str(uuid.uuid4()),
                    "filename" : fname,
                    "datetime" : datetime,
                    "entityList" : entity_names,
                    "entitySpatialMeta" : entity_spatial_metadata,
                    "entityPropMeta" : "",
                    "spatialRelationList" : "",
                    "semanticRelationList" : "",
                    "location" : location,
                    "device" : device,
                    "caption" : caption,
                    "image" : base64img
                }
        
        with open(op_filename, "w") as fp:
            json.dump(_json, fp)
        
    def _get_image_tags(self, filename, op_tags):
        result_tags = {}
        with open(filename, 'rb') as fh:
            tags = exifread.process_file(fh)
            for key in op_tags:
                if key in tags:
                    result_tags[key] = str(tags[key])
            return result_tags

    def _get_consumable_img_tags(self, tag_dict):
        result_dict = {"location":"", "datetime":"", "device":""}
        # get address using lat-lon
        lat = tag_dict["GPS GPSLatitude"] if "GPS GPSLatitude" in tag_dict else ""
        lon = tag_dict["GPS GPSLongitude"] if "GPS GPSLongitude" in tag_dict else ""
        result_dict["location"] = self.g.get_address(lat, lon)
        # get device info
        result_dict["device"] = str(tag_dict["Image Model"]) if "Image Model" in tag_dict else ""
        # convert into month-name, year
        result_dict["datetime"] = str(tag_dict["EXIF DateTimeOriginal"]) if "EXIF DateTimeOriginal" in tag_dict else ""
        return result_dict
    
    # method to get entity names and metadata for input image file name
    def _get_entities(self, fname, pickle_dir):
        _actual_filename = self._get_filename_from_path(fname)
        _actual_filename = pickle_dir + "/" + _actual_filename.split(".")[0:1][0] + ".pkl"
        _, entity_names, entity_metadata = self.unpacker.unpack(_actual_filename)
        return entity_names, entity_metadata

    def process(self, path, pickle_dir, output_dir):
        if not os.path.exists(path):
            print("path :'"+ path + "' doesn't exists.")
            return
        
        fip = open(path, "r", encoding="utf-8")
        cnt = 1
        for line in fip:
            items = line.split("\t")
            fname = items[0]
            caption = items[1]

            img_tag_keys = [ "EXIF DateTimeOriginal",
                             "GPS GPSLatitude",
                             "GPS GPSLongitude",
                             "Image Model"
                            ]
                            
            img_tags = self._get_consumable_img_tags(self._get_image_tags(fname, img_tag_keys))
            base64_img = self._get_image_base64(fname)

            _actual_filename = self._get_filename_from_path(fname)
            _actual_filename = _actual_filename.split(".")[0:1]
            _actual_filename = _actual_filename[0]

            op_filename = output_dir + "/" + _actual_filename + ".json"

            _pickle_filename = pickle_dir + "/" + _actual_filename + ".pkl"

            if os.path.exists(_pickle_filename):
                print("file exists: '" + _pickle_filename +"'")
                self._create_blob(fname, pickle_dir,  base64_img, caption, "", op_filename, img_tags["location"], img_tags["datetime"], img_tags["device"])
            else:
                print("doesn't exist : '" + _pickle_filename + "'")
            cnt+= 1
        print("Completely processed " + path)

if __name__ == "__main__":
    # path = "/Users/kartik/pycook/tensorflow_models/models/research/im2txt/mscoco_subset/mscoco_subset_gen_captions.tsv"

    path = "/Users/kartik/pycook/tensorflow_models/models/research/im2txt/mscoco_subset/generated_captions_latest.tsv"
    pickle_dir = "/Users/kartik/pycook/tensorflow_models/models/research/im2txt/mscoco_subset/pickle_files"
    output_dir = "/Users/kartik/pycook/tensorflow_models/models/research/im2txt/mscoco_subset/blob_files"

    # /Users/kartik/pycook/tensorflow_models/models/research/im2txt/mscoco_subset/sampled_images/

    b = BlobGenerator()
    b.process(path, pickle_dir, output_dir)


    # using Reverse geo encoding using geo-encoder
    # g = GeoEnodingHelper()
    # g.get_address([47, 38, 777/20], [122, 7, 2711/100])