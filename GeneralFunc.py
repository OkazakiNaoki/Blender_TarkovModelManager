import os
import json
import bpy

"""
	General	functions
"""

# Give relative path from .blend file and return json data
def GetJsonData(relPath):
	with open(bpy.path.abspath(relPath)) as json_file:
		data = json.load(json_file)
	return data

# Delete all meshes, materials and textures that unused (their target object is destroyed)
def KillUnusedItems():
	for m in bpy.data.meshes:
		if m.users == 0:
			bpy.data.meshes.remove(m)
	for mat in bpy.data.materials:
		if mat.users == 0:
			bpy.data.materials.remove(mat)
	for img in bpy.data.images:
		if img.users == 0:
			bpy.data.images.remove(img)

# Give an object and return its toppest parent object
def GetTopLevelParent(obj):
	if obj.parent is None:
		return obj
	else:
		return GetTopLevelParent(obj.parent)

# Get a list that contain all top level object in the scene
def GetTopLevelObects():
	return [o for o in bpy.context.scene.objects if not o.parent]

# Give an object, the keyword you want to search, and a list for storing results(object)
def SearchNameUnderObject(obj, keyword, matchList):
	for c in obj.children:
		if keyword in c.name:
			matchList.append(c)
			SearchNameUnderObject(c, keyword, matchList)
		elif c.children:
			SearchNameUnderObject(c, keyword, matchList)

# Give an object and a list for storing all children of that given object
def CreateChildrenList(obj, children):
	for c in obj.children:
		children.append(c)
		if c.children:
			CreateChildrenList(c, children)

# Give an object and set the hiding flag, all child objects under the given object would be selected
def SelectHierarchy(obj, unhideLOD):
	if unhideLOD and obj.hide_get():
		obj.hide_set(False)
	obj.select_set(True)
	for c in obj.children:
		if unhideLOD and c.hide_get():
			c.hide_set(False)
		c.select_set(True)
		if c.children:
			SelectHierarchy(c, unhideLOD)

# Give a object list and a flag of want to hide or not
def HideObjInList(objList, hide):
	for obj in objList:
		obj.hide_set(hide)

# Give an object and return its prefix info that contain mod type
def GetModTypeFromObjName(obj):
	name1 = obj.name.split('_')[0]
	name2 = obj.name.split('_')[0] + "_" + obj.name.split('_')[1]
	with open(bpy.path.abspath("//slot_map.json")) as json_file:
		data = json.load(json_file)
	for d in data['mod_slot']:
		if name1 == d['mod'] or name2 == d['mod']:
			return d['mod']
	return None

# Give and object and a list for storing all material inside all child objects
def GetAllMatsUnderObj(obj, matList):
	for c in obj.children:
		if len(c.material_slots) > 0:
			for cms in c.material_slots:
				if cms.material not in matList:
					matList.append(cms.material)
		if c.children:
			GetAllMatsUnderObj(c, matList)

def CreateFileListUnderPath(absPath, fileList):
	for file in os.listdir(absPath):
		if os.path.isfile(os.path.join(absPath, file)):
			fileList.append(file)