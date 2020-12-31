import os
import sys
import json
import math
import bpy
from bpy.types import Panel, PropertyGroup, Scene, WindowManager
from bpy.props import (
	IntProperty,
	EnumProperty,
	StringProperty,
	BoolProperty,
	PointerProperty,
	CollectionProperty
)

# import custom py files
# dir = os.getcwd()
# if not dir in sys.path:
# 	sys.path.append(dir )
# import GeneralFunc
# import importlib
# importlib.reload(GeneralFunc)
# from GeneralFunc import *
from .GeneralFunc import *

# Give the width of pop up message box and the string content
def SpawnMsgBox(boxWidth, boxContent):
	bpy.context.scene.uiControlProps.msgContent = boxContent
	bpy.context.scene.uiControlProps.msgPopUpLen = boxWidth
	bpy.ops.pt.spawn_msg_box('INVOKE_DEFAULT')

"""
Action
"""

# Give an object and action name then return an action clip
def GetActionByName(obj, name):
	fullActName = obj.name + '|' + name + '|' + "Base Layer"
	for act in bpy.data.actions:
		if act.name == fullActName:
			return act

# Give an object and return if the object contain animation data
def IsContainAnim(obj):
	if obj.animation_data:
		return True
	else:
		return False

# Give action name and set all object that own animation data to this action
def SetAnim(actName):
	for obj in bpy.context.scene.objects:
		if IsContainAnim(obj):
			action = GetActionByName(obj, actName)
			obj.animation_data.action = action

# Generate function for drop down list of actions
def GetActionFullList(scene, context):
	actionList = []
	for act in bpy.data.actions:
		actName = act.name.split('|')[1]
		tmpTuple = (actName, actName, "")
		if tmpTuple not in actionList:
			actionList.append(tmpTuple)
	return actionList

# Update function for drop down list of actions
def SelectAction(self, context):
	SetAnim(context.scene.uiControlProps.actionList)

"""
 Model manager general func
"""
# Return object that currently selected in Model list
def GetModelListActiveObj():
	if len(bpy.context.scene.models.keys()) > 0:
		return bpy.context.scene.objects.get(bpy.context.scene.models[bpy.context.scene.modelIdx].name, None)
	else:
		return None


"""
 LOD
"""

def HideL63Objects():
	children = []
	lodObjs = []
	CreateChildrenList(GetModelListActiveObj(), children)
	for c in children:
		if len(c.name) >= 63:
			data = GetJsonData("//L63_LOD1.json")
			for d in data["L63lod1"]:
				if d["root_name"] == GetModelListActiveObj().name and d["lod1_name"] == c.name:
					lodObjs.append(c)
	HideObjInList(lodObjs, True)

# Update function for hide LOD1 mesh button
def HideInViewport(hideFlag):
	selected = GetModelListActiveObj()
	lodObjs = []
	
	if selected:
		SearchNameUnderObject(selected, "LOD1", lodObjs)
		if len(lodObjs)>0:
			if(hideFlag):
				HideObjInList(lodObjs, True)
				GetModelListActiveProp().lod1MeshHided = True
			else:
				HideObjInList(lodObjs, False)
				GetModelListActiveProp().lod1MeshHided = False

"""
 Texture
"""
# Clear all string that previously set in these string property
def ClearTexPathBox():
	bpy.context.scene.texPathLabel.diffusePath = ""
	bpy.context.scene.texPathLabel.specularPath = ""
	bpy.context.scene.texPathLabel.glossnessPath = ""
	bpy.context.scene.texPathLabel.normalPath = ""

# Update function for shader type drop down list
def UpdateTexPathBox(self, context):
	texTypeList = GetShaderTexTypeList()
	if "spec" in texTypeList:
		bpy.context.scene.texPathLabel.enableSpec = True
	else:
		bpy.context.scene.texPathLabel.enableSpec = False
	if "gloss" in texTypeList:
		bpy.context.scene.texPathLabel.enableGloss = True
	else:
		bpy.context.scene.texPathLabel.enableGloss = False
	ClearTexPathBox()

# Give a string of mod type and return the relative path of texture folder which contain that kind of mod type
def GetTexPath(modType):
	data = GetJsonData("//texture_paths.json")
	for d in data['items']:
		if modType == d['item_type']:
			return d['texture_path']
	return None

# Initialize function for texture path drop down list
def ReadTexPath(scene, context):
	texPaths = []
	data = GetJsonData("//texture_paths.json")
	for d in data['items']:
		texPaths.append((d['texture_path'], d['item_type'], ""))
	return texPaths

# Return a list of all texture types which needed by choosed shader
def GetShaderTexTypeList():
	data = GetJsonData("//shaders.json")
	for d in data['shaders']:
		if d['shader_name'] == bpy.context.scene.uiControlProps.shader:
			return d['texture_types']

# Return a dictionary that contain all texture it found (texType - texPath)
def GetTexturePaths():
	relPath = bpy.context.scene.uiControlProps.textureFolderPath
	absPath = bpy.path.abspath(relPath)
	matName = GetMaterial().name
	files = []
	paths = {}

	# check the existance of path of assigned folder
	if os.path.exists(absPath):
		CreateFileListUnderPath(absPath, files)
	else:
		SpawnMsgBox(500, "[texture] : the texture folder path is not exist.")
		return None

	# get texture types of shader
	texTypeList = GetShaderTexTypeList()
	
	# try search the texture name under json files (the fucking hard way)
	for tt in texTypeList:
		path = FindTexNameInJson(tt)
		if path != None and os.path.exists(bpy.path.abspath(path)):
			paths[tt] = path
		elif path != None and not os.path.exists(bpy.path.abspath(path)):
			SpawnMsgBox(500, "[texture] : the " + tt + " texture file path is not exist.")
		
	# try to get texture name from material name (the most simple way)
	referName = matName
	for f in files:
		if referName in f:
			if('diff' in f and 'diff' not in paths.keys()):
				paths['diff'] = relPath + "/" + f
			if('spec' in f and 'spec' not in paths.keys()):
				paths['spec'] = relPath + "/" + f
			if('glos' in f and 'gloss' not in paths.keys()):
				paths['gloss'] = relPath + "/" + f
			if('nrm' in f and 'nrm' not in paths.keys()):
				paths['nrm'] = relPath + "/" + f
	return paths

# Give a texture type string and try find the texture of given type in json files, if found return relative file path
def FindTexNameInJson(texType):
	texSearchMode = bpy.context.scene.uiControlProps.texSearchMode
	colorSuffix = bpy.context.scene.uiControlProps.colorSuffix
	texFolder = bpy.context.scene.uiControlProps.textureFolderPath
	rootObjName = GetMatListActiveProp().rootObjName
	actMatName = GetMatListActiveProp().material.name

	if texSearchMode == "general":
		# material name longer than 63 characters
		if len(actMatName) >= 63:
			data = GetJsonData("//L63_texture.json")
			for d in data['L63']:
				if d['root_name'] == rootObjName and d['material_name'] == actMatName:
					return GetTexPath(d['mod_type']) + "/" + d['texture_name'] + "_" + texType + ".tga"
		# manually matching texture name by json file
		data = GetJsonData("//manual_texture.json")
		for d in data['manual']:
			if d['root_name'] == rootObjName and d['material_name'] == actMatName:
				if colorSuffix == 'no':
					return texFolder + "/" + d['texture_name'] + "_" + texType + ".tga"
				else:
					return ProcessColorSuffixPath(d['texture_name'], texType)
		# non-manually matching texture that need color suffix
		if colorSuffix != 'no':
			return ProcessColorSuffixPath(actMatName, texType)
	elif texSearchMode == "share":
		# use share texture that used by other mod types
		data = GetJsonData("//share_texture.json")
		for d in data['share']:
			if d['root_name'] == rootObjName and d['material_name'] == actMatName:
				return GetTexPath(d['mod_type']) + "/" + d['texture_name'] + "_" + texType + ".tga"
	return None

# Give string of texture full name and type of texture, return relative file path with color suffix
def ProcessColorSuffixPath(texFullName, texType):
	texFolder = bpy.context.scene.uiControlProps.textureFolderPath
	colorSuffix = bpy.context.scene.uiControlProps.colorSuffix
	if colorSuffix == "diff":
		if "_diff_" in texFullName:
			if texType == "diff":
				path = texFolder + "/" + texFullName + ".tga"
			else:
				texName = texFullName.split("_diff_")[0]
				color = texFullName.split("_diff_")[1]
				path = texFolder + "/" + texName + "_" + texType + ".tga"
		elif "_diff_" not in texFullName:
			texName = texFullName.rsplit('_', 1)[0]
			color = texFullName.split('_')[-1]
			if texType == "diff":
				path = texFolder + "/" + texName + "_" + texType + "_" + color + ".tga"
			else:
				path = texFolder + "/" + texName + "_" + texType + ".tga"
	elif colorSuffix == "all":
		color = texFullName.split('_')[-1]
		texName = texFullName.rsplit('_', 1)[0]
		path = texFolder + "/" + texName + "_" + texType + "_" + color + ".tga"
	return path

"""
 Material
"""
# Return the selected model in model list
def GetModelListActiveProp():
	if len(bpy.context.scene.models.keys()) > 0:
		return bpy.context.scene.models[bpy.context.scene.modelIdx]
	else:
		return None

def GetModelListPropByName(name):
	for mdl in bpy.context.scene.models:
		if mdl.name == name:
			return mdl
	return None

# Return selected material prop in material list
def GetMatListActiveProp():
	return GetModelListActiveProp().matList[GetModelListActiveProp().matListIdx]

# Return selected material from material list
def GetMaterial():
	matIdx = GetModelListActiveProp().matListIdx
	matList = GetModelListActiveProp().matList
	if len(matList.keys()) > 0:
		return matList[matIdx].material
	else:
		return None

# Give nodes from any material and clear all nodes inside it
def ClearMaterialNodes(nodes):
	for n in nodes:
		nodes.remove(n)

# Generate shader nodes for selected material in material list
def GenerateMat():
	if not bpy.data.is_saved:
		SpawnMsgBox(150, "please save blend file")
	else:
		bpy.context.scene.uiControlProps.curColCount = 0
		bpy.context.scene.uiControlProps.curOrderCount = 0

		mat = GetMaterial()
		if mat == None:
			SpawnMsgBox(200, "no material selected")
			return
		mat.use_nodes = True
		nodes = mat.node_tree.nodes
		links = mat.node_tree.links
		# reset all shader nodes inside the material
		ClearMaterialNodes(nodes)
		bpy.context.scene.deployedNodes.clear()
		# try get the texture path dictionary
		paths = GetTexturePaths()
		# create base shader and output node
		AddPbrShader(nodes, links, paths)
				
		workflow = bpy.context.scene.uiControlProps.shader
		# create diffuse/spec/gloss node
		if workflow == "Tarkov":
			bsdf = GetNodeFromDict(nodes, 'bsdf')
			links.new(AddPbrAlbedoNodes(nodes, links, None, paths), bsdf.inputs['Base Color'])
			albedoAlpha = GetNodeFromDict(nodes, 'albedo').outputs['Alpha']
			links.new(AddPbrSpecularNodes(nodes, links, albedoAlpha, paths), bsdf.inputs['Specular'])
			links.new(AddPbrGlossNodes(nodes, links, None, paths), bsdf.inputs['Roughness'])
		elif workflow == "Unity1":
			bsdf = GetNodeFromDict(nodes, 'bsdf')
			links.new(AddPbrAlbedoNodes(nodes, links, None, paths), bsdf.inputs['Base Color'])
			albedoAlpha = GetNodeFromDict(nodes, 'albedo').outputs['Alpha']
			links.new(AddPbrSpecularNodes(nodes, links, None, paths), bsdf.inputs['Specular'])
			bpy.context.scene.uiControlProps.curColCount -= 1
			links.new(AddPbrGlossNodes(nodes, links, albedoAlpha, paths), bsdf.inputs['Roughness'])
		elif workflow == "Unity2":
			bsdf = GetNodeFromDict(nodes, 'bsdf')
			links.new(AddPbrAlbedoNodes(nodes, links, None, paths), bsdf.inputs['Base Color'])
			links.new(AddPbrSpecularNodes(nodes, links, None, paths), bsdf.inputs['Specular'])
			bpy.context.scene.uiControlProps.curColCount -= 1
			specAlpha = GetNodeFromDict(nodes, 'spec').outputs['Alpha']
			links.new(AddPbrGlossNodes(nodes, links, specAlpha, paths), bsdf.inputs['Roughness'])
		elif workflow == "AllSep":
			bsdf = GetNodeFromDict(nodes, 'bsdf')
			links.new(AddPbrAlbedoNodes(nodes, links, None, paths), bsdf.inputs['Base Color'])
			links.new(AddPbrSpecularNodes(nodes, links, None, paths), bsdf.inputs['Specular'])
			links.new(AddPbrGlossNodes(nodes, links, None, paths), bsdf.inputs['Roughness'])			
		# normal map
		nrmNeedFix = bpy.context.scene.uiControlProps.nrmNeedFix
		links.new(AddPbrNormalNodes(nodes, links, None, paths, nrmNeedFix), bsdf.inputs['Normal'])
		# make node tree looks better
		SpreadOutNodes(nodes)
		# display final texture path in string
		UpdateTexPathLabel()

"""
 Node location
"""
# Give node and node name string then create a record in deployedNodes property
def StoreLocXY(node, nodeName):
	newNode = bpy.context.scene.deployedNodes.add()
	newNode.nodeKey = node.name
	newNode.name = nodeName
	newNode.nodeColumn = bpy.context.scene.uiControlProps.curColCount

# Give nodes of a material and node name string then return the node inside nodes which match the name given
def GetNodeFromDict(nodes, nodeName):
	for n in bpy.context.scene.deployedNodes:
		if n.name == nodeName:
			return nodes.get(n.nodeKey)

# Give nodes of a material and follow what was recorded in deployedNodes property to spread node position in shader editor
def SpreadOutNodes(nodes):
	locX = 0
	curCol = 2
	maxLocX = 0
	for n in bpy.context.scene.deployedNodes:
		if n.nodeColumn > 1:
			if curCol != n.nodeColumn:
				curCol += 1
				locX = 0
			node = GetNodeFromDict(nodes, n.name)
			node.location.x = locX
			locX += (node.width + 50)
			if locX > maxLocX:
				maxLocX = locX
			node.location.y = (curCol-2)*(-300)
	node = GetNodeFromDict(nodes, 'bsdf')
	node.location.x = maxLocX
	maxLocX += (node.width + 50)
	GetNodeFromDict(nodes, 'matout').location.x = maxLocX

"""
 UI-related methods
"""

def AddModelToList(impObj):
	if bpy.data.is_saved:
		objPrefix = GetModTypeFromObjName(impObj)
		if objPrefix:
			if objPrefix == "weapon":
				bpy.context.scene.dataColl.weaponBodyCount+=1
			newModel = bpy.context.scene.models.add()
			newModel.modType = objPrefix
			newModel.name = impObj.name
			newModel.installed = False
			newModel.reassignModType = "not set"
			newModel.lod1MeshHided = False

def AddMatsToList(selected):
	if not GetModelListActiveProp().matListCreated:
		matList = []
		#existList = GetModelListActiveProp().matList.keys()
		GetAllMatsUnderObj(selected, matList)

		if not bpy.context.scene.uiControlProps.showLod1Mat:
			matList = [x for x in matList if "LOD1" not in x.name]

		for ml in matList:
			newMat = GetModelListActiveProp().matList.add()
			newMat.name = ml.name
			newMat.material = ml
			newMat.matType = "default"
			newMat.rootObjName = GetTopLevelParent(selected).name
		GetModelListActiveProp().matListCreated = True

def CreateEmptyMat():
	if GetModelListActiveProp().matListCreated:
		if bpy.context.selected_objects[0]:
			newMat = GetModelListActiveProp().matList.add()
			newMat.name = bpy.context.selected_objects[0].name
			newMat.material = bpy.data.materials.new(name=bpy.context.selected_objects[0].name)
			newMat.matType = "new"
			newMat.rootObjName = bpy.context.scene.dataColl.activeModelName

def KillMat():
	if GetModelListActiveProp().matListCreated:
		matIdx = GetModelListActiveProp().matListIdx
		matList = GetModelListActiveProp().matList
		mat = GetMaterial()
		bpy.data.materials.remove(mat)
		matList.remove(matIdx)

def UpdateAttachData():
	ucp = bpy.context.scene.uiControlProps
	selected = bpy.context.scene.objects.get(GetModelListActiveProp().name)

	RenewTheSlot(0)

	bpy.context.view_layer.objects.active = None
	bpy.context.view_layer.objects.active = selected
	bpy.ops.object.select_all(action='DESELECT')
	SelectHierarchy(selected, False)

	if GetModelListActiveProp().modType == "weapon":
		ucp.enableAttachFunc = False
	else:
		ucp.enableAttachFunc = True

	if GetModelListActiveProp().installed:
		ucp.attachBtnStr = "Detach"
	else:
		ucp.attachBtnStr = "Attach"

def OnClickModelListUpdate(self, context):
	ucp = bpy.context.scene.uiControlProps
	idx = bpy.context.scene.modelIdx
	impMdls = bpy.context.scene.models
	selected = bpy.context.scene.objects.get(impMdls[idx].name)
	bpy.context.scene.dataColl.activeModelName = selected.name
	UpdateAttachData()
	AddMatsToList(selected)
	#ucp.disableLod1Mesh = not impMdls[idx].lod1MeshHided
	if impMdls[idx].installed:
		ucp.enableReassign = False
	else:
		ucp.enableReassign = True
	ClearTexPathBox()

def OnClickMatListUpdate(self, context):
	UpdateTexPathLabel()

def HideTexFolderSelection(self, context):
	if bpy.context.scene.uiControlProps.texSearchMode == 'share':
		bpy.context.scene.uiControlProps.enableTexFolderSelection = False
	else:
		bpy.context.scene.uiControlProps.enableTexFolderSelection = True

def UpdateTexPathLabel():
	bpy.context.scene.texPathLabel.diffusePath = GetMatListActiveProp().texPathInfo.diffusePath
	bpy.context.scene.texPathLabel.specularPath = GetMatListActiveProp().texPathInfo.specularPath
	bpy.context.scene.texPathLabel.glossnessPath = GetMatListActiveProp().texPathInfo.glossnessPath
	bpy.context.scene.texPathLabel.normalPath = GetMatListActiveProp().texPathInfo.normalPath
	

def UpdateReassignMod(scene, context):
	RenewTheSlot(0)

def CreateShaderList(scene, context):
	shaders = []
	data = GetJsonData("//shaders.json")
	for d in data['shaders']:
		shaders.append((d['shader_name'], d['description'], ""))
	return shaders

def CreateModList(scene, context):
	mod = []
	data = GetJsonData("//mod_and_slot.json")
	for d in data['mod_and_slot']:
		mod.append((d['mod'], d['mod'], ""))
	return mod


"""
 Attachment related
"""

def UpdateModelList():
	models = bpy.context.scene.models
	for impObj in models:
		found = False
		for obj in bpy.context.scene.objects:
			if impObj.name == obj.name:
				found = True
				break
		if not found:
			models.remove(models.find(impObj.name))
		
def GetMainWeaponBody():
	for impObj in bpy.context.scene.models:
		if impObj.modType == "weapon":
			return bpy.context.scene.objects.get(impObj.name)
	return None

def GetClosestParentModel(obj):
	if obj.parent:
		if obj.parent.name in [mdl.name for mdl in bpy.context.scene.models]:
			return obj.parent.name
		else:
			return GetClosestParentModel(obj.parent)

def GetSlotsByObject(modObj, weaponBody):
	result = []
	with open(bpy.path.abspath("//slot_map.json")) as json_file:
		data = json.load(json_file)
	for d in data['mod_slot']:
		if d['mod'] in modObj.name:
			if type(d['slot']) is list:
				for s in d['slot']:
					slot=[]
					SearchNameUnderObject(weaponBody, s, slot)
					result.extend(slot)
			else:
				SearchNameUnderObject(weaponBody, d['slot'], result)
	return result

def GetSlotsByModType(modType, weaponBody):
	result = []
	with open(bpy.path.abspath("//mod_and_slot.json")) as json_file:
		data = json.load(json_file)
	for d in data['mod_and_slot']:
		if d['mod'] == modType:
			SearchNameUnderObject(weaponBody, d['slot'], result)
	return result

def AddChildToModelProp(parentName, childName):
	child = GetModelListPropByName(parentName).childModels.add()
	child.name = childName
	GetModelListActiveProp().parentModel = parentName

def DelChildFromModelProp(parentName, childName):
	childList = GetModelListPropByName(parentName).childModels
	childList.remove(childList.find(childName))
	GetModelListActiveProp().parentModel = ""

def AttachModToWeapon():
	idx = bpy.context.scene.modelIdx
	try:
		item = bpy.context.scene.models[idx]
	except IndexError:
		return
	impObj = bpy.context.scene.models[idx]
	bpy.ops.object.select_all(action='DESELECT')
	selected = bpy.context.scene.objects.get(impObj.name)

	if bpy.context.scene.dataColl.weaponBodyCount == 1:
		if impObj.installed:
			if len(GetModelListActiveProp().childModels) > 0:
				SpawnMsgBox(400, "please remove child mod(s) installed on it first")
				return
			else:
				parentModel = GetModelListPropByName(GetClosestParentModel(selected.parent))
				if parentModel.modType == "weapon":
					parentModel.installed = False
				# update child for parent obj (remove)
				DelChildFromModelProp(parentModel.name, selected.name)
				# set object's new parent
				selected.parent = None
				bpy.ops.object.origin_clear()
				impObj.installed = False
				bpy.context.scene.dataColl.modInstallCount -= 1
				bpy.context.scene.uiControlProps.attachBtnStr = "Attach"
				RenewTheSlot(0)
				bpy.context.scene.uiControlProps.enableReassign = True
				return
		else:
			weaponBody = GetMainWeaponBody()
			if weaponBody == None:
				SpawnMsgBox(300, "check if weapon main body was imported")
				return
			else:
				slot = []
				if impObj.reassignModType != "not set":
					slot = GetSlotsByModType(impObj.reassignModType, weaponBody)
				else:
					slot = GetSlotsByObject(selected, weaponBody)
				if len(slot) > 0:
					parentModel = GetModelListPropByName(GetClosestParentModel(slot[0]))
					if parentModel.modType == "weapon":
						parentModel.installed = True
					# update child for parent obj (add)
					AddChildToModelProp(parentModel.name, selected.name)
					# set object's new parent
					selected.parent = slot[0]
					bpy.ops.object.origin_clear()
					impObj.installed = True
					bpy.context.scene.dataColl.modInstallCount += 1
					bpy.context.scene.uiControlProps.attachBtnStr = "Detach"
					RenewTheSlot(0)
					bpy.context.scene.uiControlProps.enableReassign = False
					return
				else:
					SpawnMsgBox(300, "the slot is not under weapon body yet, install other mods first")
					return
	elif bpy.context.scene.dataColl.weaponBodyCount == 0:
		SpawnMsgBox(250, "main weapon body is not yet import")
	elif bpy.context.scene.dataColl.weaponBodyCount > 1:
		SpawnMsgBox(250, "more than 1 main weapon body exist")

def RenewTheSlot(newTarget=0):
	idx = bpy.context.scene.modelIdx
	try:
		item = bpy.context.scene.models[idx]
	except IndexError:
		return
	weaponBody = GetMainWeaponBody()
	impObj = bpy.context.scene.models[idx]
	selected = bpy.context.scene.objects.get(impObj.name)
	installed = impObj.installed
	if weaponBody:
		slotList = []
		if impObj.reassignModType != "not set":
			slotList = GetSlotsByModType(impObj.reassignModType, weaponBody)
		else:
			slotList = GetSlotsByObject(selected, weaponBody)
		
		excludeList = []
		CreateChildrenList(selected, excludeList)
		for exc in excludeList:
			if exc in slotList:
				slotList.remove(exc)
		
		curModSlot = selected.parent
		if newTarget == 0:
			if installed and curModSlot!=None:
				bpy.context.scene.uiControlProps.modSlotNumStr = str(slotList.index(curModSlot)+1) + " / " + str(len(slotList))
			else:
				bpy.context.scene.uiControlProps.modSlotNumStr = "0 / " + str(len(slotList))
		elif newTarget == 1 and installed:
			listLen = len(slotList)
			if slotList.index(curModSlot)+1 != listLen:
				parentModel = GetModelListPropByName(GetClosestParentModel(curModSlot))
				DelChildFromModelProp(parentModel.name, selected.name)
				parentModel = GetModelListPropByName(GetClosestParentModel(slotList[slotList.index(curModSlot)+1]))
				AddChildToModelProp(parentModel.name, selected.name)
				selected.parent = slotList[slotList.index(curModSlot)+1]
				bpy.ops.object.origin_clear()
			else:
				parentModel = GetModelListPropByName(GetClosestParentModel(curModSlot))
				DelChildFromModelProp(parentModel.name, selected.name)
				parentModel = GetModelListPropByName(GetClosestParentModel(slotList[0]))
				AddChildToModelProp(parentModel.name, selected.name)
				selected.parent = slotList[0]
				bpy.ops.object.origin_clear()
			bpy.context.scene.uiControlProps.modSlotNumStr = str(slotList.index(selected.parent)+1) + " / " + str(len(slotList))
		elif newTarget == -1 and installed:
			listLen = len(slotList)
			if slotList.index(curModSlot)-1 != -1:
				parentModel = GetModelListPropByName(GetClosestParentModel(curModSlot))
				DelChildFromModelProp(parentModel.name, selected.name)
				parentModel = GetModelListPropByName(GetClosestParentModel(slotList[slotList.index(curModSlot)-1]))
				AddChildToModelProp(parentModel.name, selected.name)
				selected.parent = slotList[slotList.index(curModSlot)-1]
				bpy.ops.object.origin_clear()
			else:
				parentModel = GetModelListPropByName(GetClosestParentModel(curModSlot))
				DelChildFromModelProp(parentModel.name, selected.name)
				parentModel = GetModelListPropByName(GetClosestParentModel(slotList[len(slotList)-1]))
				AddChildToModelProp(parentModel.name, selected.name)
				selected.parent = slotList[len(slotList)-1]
				bpy.ops.object.origin_clear()
			bpy.context.scene.uiControlProps.modSlotNumStr = str(slotList.index(selected.parent)+1) + " / " + str(len(slotList))

		DisplayCurSlotType(selected, installed)

def DisplayCurSlotType(modObj, installed):
	data = GetJsonData("//slot_map.json")
	if installed and modObj.parent != None:
		for d in data['mod_slot']:
			if type(d['slot']) == list:
				for s in d['slot']:
					if s in modObj.parent.name:
						data2 = GetJsonData("//mod_and_slot.json")
						for mas in data2['mod_and_slot']:
							if mas['slot'] == s:
								bpy.context.scene.uiControlProps.curSlotType = mas['mod']
						return
			else:
				if d['slot'] in modObj.parent.name:
					data2 = GetJsonData("//mod_and_slot.json")
					for mas in data2['mod_and_slot']:
						if mas['slot'] == d['slot']:
							bpy.context.scene.uiControlProps.curSlotType = mas['mod']
					return
	else:
		bpy.context.scene.uiControlProps.curSlotType = ""

"""
 Shader nodes generate
"""

def AddPbrShader(nodes, links, paths):
	bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
	StoreLocXY(bsdf, 'bsdf') # col 0
	bpy.context.scene.uiControlProps.curColCount += 1
	matout = nodes.new(type="ShaderNodeOutputMaterial")
	StoreLocXY(matout, 'matout', ) # col 1
	bpy.context.scene.uiControlProps.curColCount += 1
	links.new(bsdf.outputs["BSDF"], matout.inputs["Surface"])
	bsdf.inputs["Metallic"].default_value = 0.0
	bsdf.inputs["Specular"].default_value = 0.0

def AddPbrAlbedoNodes(nodes, links, difSrcOut, paths):
	albedo = None
	if(difSrcOut == None):
		albedo = nodes.new("ShaderNodeTexImage")
		StoreLocXY(albedo, 'albedo')
		if 'diff' in paths.keys():
			GetMatListActiveProp().texPathInfo.diffusePath = paths['diff']
			albedo.image = bpy.data.images.load(paths['diff'])
			albedo.image.colorspace_settings.name = "sRGB"
		else:
			GetMatListActiveProp().texPathInfo.diffusePath = "not found"
		bpy.context.scene.uiControlProps.curColCount += 1
		return albedo.outputs['Color']

def AddPbrSpecularNodes(nodes, links, difSrcOut, paths):
	spec = None
	if difSrcOut == None:
		spec = nodes.new("ShaderNodeTexImage")
		StoreLocXY(spec, 'spec')
		if 'spec' in paths.keys():
			GetMatListActiveProp().texPathInfo.specularPath = paths['spec']
			spec.image = bpy.data.images.load(paths['spec'])
			spec.image.colorspace_settings.name = "Non-Color"
		else:
			GetMatListActiveProp().texPathInfo.specularPath = "not found"
		bpy.context.scene.uiControlProps.curColCount += 1
		return spec.outputs["Color"]
	else:
		return difSrcOut

def AddPbrGlossNodes(nodes, links, difSrcOut, paths):
	glos = None
	if difSrcOut == None:
		glos = nodes.new("ShaderNodeTexImage")
		StoreLocXY(glos, 'glos')
		if 'gloss' in paths.keys():
			GetMatListActiveProp().texPathInfo.glossnessPath = paths['gloss']
			glos.image = bpy.data.images.load(paths['gloss'])
			glos.image.colorspace_settings.name = "Non-Color"
		else:
			GetMatListActiveProp().texPathInfo.glossnessPath = "not found"
	glosInv = nodes.new(type="ShaderNodeInvert")
	StoreLocXY(glosInv, 'glosInv')
	if difSrcOut == None:
		links.new(glos.outputs["Color"], glosInv.inputs["Color"])
	else:
		links.new(difSrcOut, glosInv.inputs["Color"])
	bpy.context.scene.uiControlProps.curColCount += 1
	return glosInv.outputs["Color"]

def AddPbrNormalNodes(nodes, links, difSrcOut, paths, reqFix):
	nrm = None
	if difSrcOut == None:
		nrm = nodes.new("ShaderNodeTexImage")
		StoreLocXY(nrm, 'nrm')
		if 'nrm' in paths.keys():
			GetMatListActiveProp().texPathInfo.normalPath = paths['nrm']
			nrm.image = bpy.data.images.load(paths['nrm'])
			nrm.image.colorspace_settings.name = "Non-Color"
		else:
			GetMatListActiveProp().texPathInfo.normalPath = "not found"
	nrmMap = nodes.new(type="ShaderNodeNormalMap")
	if reqFix:
		nrmSepRGB = nodes.new(type="ShaderNodeSeparateRGB")
		StoreLocXY(nrmSepRGB, 'nrmSepRGB')
		nrmCbnRGB = nodes.new(type="ShaderNodeCombineRGB")
		StoreLocXY(nrmCbnRGB, 'nrmCbnRGB')
		links.new(nrm.outputs["Color"], nrmSepRGB.inputs["Image"])
		links.new(nrmSepRGB.outputs["G"], nrmCbnRGB.inputs["G"])
		links.new(nrm.outputs["Alpha"], nrmCbnRGB.inputs["R"])
		nrmCbnRGB.inputs["B"].default_value = 1.0
		links.new(nrmCbnRGB.outputs["Image"], nrmMap.inputs["Color"])
	else:
		links.new(nrm.outputs["Color"], nrmMap.inputs["Color"])
	StoreLocXY(nrmMap, 'nrmMap')
	bpy.context.scene.uiControlProps.curColCount += 1
	return nrmMap.outputs["Normal"]

"""
 Properties
"""

class UIControlProps(PropertyGroup):
	actionList: EnumProperty(
		items = GetActionFullList,
		update = SelectAction
	)
	disableLod1Mesh: BoolProperty(
		default = True
		#update = lambda s, c: HideInViewport(s, c, s.disableLod1Mesh)
	)
	showLod1Mat: BoolProperty(
		default=False
	)
	shader: EnumProperty(
		items = CreateShaderList,
		update= UpdateTexPathBox,
		name = "select one of these workflows. D:diffuse S:specular G:glossness N:normal",
		description = "",
	)
	nrmNeedFix: BoolProperty(
		description = "if normal map is red, check this",
		default = True
	)
	msgContent: StringProperty()
	msgPopUpLen: IntProperty(
		default = 300
	)
	textureFolderPath: EnumProperty(
		items = ReadTexPath,
		name = "folder name under texture folder"
	)
	curColCount: IntProperty()
	texSearchMode: EnumProperty(
        items=[
            ('general', 'general', "just try material name, no promise would found", '', 0),
			('share', 'share', "use a texture shared by other mods or weapons", '', 1)
        ],
        default='general',
		update = HideTexFolderSelection
    )
	colorSuffix: EnumProperty(
        items=[
			('no', 'no', "file have no color suffix", '', 0),
            ('diff', 'diff', "Only diffuse texture file have color suffix", '', 1),
            ('all', 'all', "all texture file have color suffix", '', 2)
        ],
        default='no'
    )
	curSlotType: StringProperty()
	modSlotNumStr: StringProperty()
	enableAttachFunc: BoolProperty(default=True)
	attachBtnStr: StringProperty(default="Attach")
	enableReassign: BoolProperty(default=True)
	enableTexFolderSelection: BoolProperty(default=True)
	
class DataCollection(PropertyGroup):
	weaponBodyCount: IntProperty(default=0)
	modInstallCount: IntProperty(default=0)
	activeModelName: StringProperty(default="")

class ShaderNodeDeployed(PropertyGroup):
	name: StringProperty()
	nodeKey: StringProperty()
	nodeColumn: IntProperty()

class TexturePathInfo(PropertyGroup):
	diffusePath: StringProperty(default="not set")
	specularPath: StringProperty(default="not set")
	glossnessPath: StringProperty(default="not set")
	normalPath: StringProperty(default="not set")
	enableSpec: BoolProperty(default=False)
	enableGloss: BoolProperty(default=True)

class MaterialListOfModel(PropertyGroup):
	name: StringProperty()
	material: PointerProperty(type=bpy.types.Material)
	matType: StringProperty()
	rootObjName: StringProperty()
	texPathInfo: PointerProperty(type=TexturePathInfo)

class ChildMods(PropertyGroup):
	name: StringProperty()

class TarkovModelList(PropertyGroup):
	name: StringProperty()
	modType: StringProperty()
	installed: BoolProperty()
	reassignModType: EnumProperty(
		items=CreateModList,
		update=UpdateReassignMod
	)
	lod1MeshHided: BoolProperty()
	matListCreated: BoolProperty(default=False)
	matList: CollectionProperty(type=MaterialListOfModel)
	matListIdx: IntProperty(update=OnClickMatListUpdate)
	modInstallLayer: IntProperty(default=0)
	parentModel: StringProperty(default="")
	childModels: CollectionProperty(type=ChildMods)

"""
 Panels
"""

class TarkovModelUIList(bpy.types.UIList):
	def draw_item(self, context, layout, data, item, icon, active_data, active_propnamem):
		if self.layout_type in {'DEFAULT', 'COMPACT'}:
			split = layout.split(factor=0.2)
			split.label(text=item.modType)
			split2 = split.split(factor=0.8)
			split2.label(text=item.name)
			installedText = "NO"
			if item.installed:
				installedText = "YES"
			split2.label(text=installedText)
		elif self.layout_type in {'GRID'}:
			layout.alignment = 'CENTER'
			layout.label(text="")
	def invoke(self, context, event):
		pass

class MaterialUIList(bpy.types.UIList):
	def draw_item(self, context, layout, data, item, icon, active_data, active_propnamem):
		if self.layout_type in {'DEFAULT', 'COMPACT'}:
			split = layout.split(factor=0.8)
			split.prop(item.material, "name", text="", emboss=False, icon_value=layout.icon(item.material))
			split.label(text=item.matType)
		elif self.layout_type in {'GRID'}:
			layout.alignment = 'CENTER'
			layout.label(text="")
	def invoke(self, context, event):
		pass

class ImportedModelManagePanel(bpy.types.Panel):
	bl_idname = "ADDON_PT_TARKOV_MODEL_MANAGER"
	bl_label = "Tarkov model manager"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "TMM"
	def draw(self, context):
		layout = self.layout
		ucp = context.scene.uiControlProps
		layout.operator("pt.open_fbx_browser")
		layout.separator()
		split = layout.split(factor=0.2)
		split.label(text="Mod type:")
		split2 = split.split(factor=0.78)
		split2.label(text="Name:")
		split2.label(text="Installed:")
		layout.template_list("TarkovModelUIList", "", bpy.context.scene, "models", bpy.context.scene, "modelIdx")
		layout.separator()
		col = layout.column()
		col.operator("pt.delete_model", text="Delete hierarchy")
		layout.separator()
		

class AttachSubPanel(bpy.types.Panel):
	bl_parent_id = "ADDON_PT_TARKOV_MODEL_MANAGER"
	bl_idname = "SUB_PT_MODEL_ATTACHER"
	bl_label = "Attacher"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	def draw(self, context):
		layout = self.layout
		ucp = context.scene.uiControlProps
		layout.enabled = ucp.enableAttachFunc
		
		col = layout.column()
		col.operator("pt.attach_mod", text=bpy.context.scene.uiControlProps.attachBtnStr)
		#col.operator("pt.i_am_a_tester")
		row = layout.row()
		row.operator("pt.attach_prev_mod_slot")
		row.alignment = 'CENTER'
		row.label(text=bpy.context.scene.uiControlProps.modSlotNumStr)
		row.alignment = 'EXPAND'
		row.operator("pt.attach_next_mod_slot")
		col = layout.column()
		col.label(text="Current mod slot  :  " + ucp.curSlotType)
		# part of manually rotating adjust
		row = layout.row()
		row.label(text="Rotation:")
		row.operator("pt.rotate_x_obj", text="X+90")
		row.operator("pt.rotate_y_obj", text="Y+90")
		row.operator("pt.rotate_z_obj", text="Z+90")
		col = layout.column()
		col.enabled = ucp.enableReassign
		if len(bpy.context.scene.models) > 0:
			col.prop(GetModelListActiveProp(), "reassignModType", text="Reassign mod type ")

class HideLodPanel(bpy.types.Panel):
	bl_parent_id = "ADDON_PT_TARKOV_MODEL_MANAGER"
	bl_idname = "SUB_PT_LOD_HIDER"
	bl_label = "LOD1 Hider"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	def draw(self, context):
		layout = self.layout
		ucp = context.scene.uiControlProps
		layout.label(text="Viewport mesh display:")
		col = layout.column()
		col.prop(ucp, "disableLod1Mesh", text="Automatically hide LOD1 meshes after import")
		col.prop(ucp, "showLod1Mat", text="List all material include LOD1")
		#col.prop(ucp, "disableLod1Mesh", toggle=True, text=lodBtnLabel)

class MaterialGeneratePanel(bpy.types.Panel):
	bl_parent_id = "ADDON_PT_TARKOV_MODEL_MANAGER"
	bl_idname = "SUB_PT_MAT_GENERATOR"
	bl_label = "Material generator"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	def draw(self, context):
		layout = self.layout
		ucp = context.scene.uiControlProps
		enableSpec = bpy.context.scene.texPathLabel.enableSpec
		specLabel = "S : " + bpy.context.scene.texPathLabel.specularPath if enableSpec else "no use in this shader"
		enableGloss = bpy.context.scene.texPathLabel.enableGloss
		glossLabel = "G : " + bpy.context.scene.texPathLabel.glossnessPath if enableGloss else "no use in this shader"

		layout.label(text="Material:")
		
		if GetModelListActiveProp() != None:
			col = layout.column()
			row = col.row()
			row.operator("pt.add_new_material")
			row.operator("pt.delete_material")
			col.template_list("MaterialUIList", "", GetModelListActiveProp(), "matList", GetModelListActiveProp(), "matListIdx")
		col = layout.column()
		col.prop(ucp, "shader", text="shader")
		box = layout.box()
		
		box.label(text="D : " + bpy.context.scene.texPathLabel.diffusePath)
		col = box.column()
		col.enabled = enableSpec
		col.label(text=specLabel)
		col = box.column()
		col.enabled = enableGloss
		col.label(text=glossLabel)
		box.label(text="N : " + bpy.context.scene.texPathLabel.normalPath)

		row = layout.row()
		row.prop(ucp, "texSearchMode", expand=True)
		row = layout.row()
		row.prop(ucp, "colorSuffix", expand=True)
		col = layout.column()
		col.enabled = ucp.enableTexFolderSelection
		col.prop(ucp, "textureFolderPath", text="mod type")
		col = layout.column()
		col.prop(ucp, "nrmNeedFix", text="normal need to fix")
		layout.operator("pt.set_material")

class AnimationSelectPanel(bpy.types.Panel):
	bl_parent_id = "ADDON_PT_TARKOV_MODEL_MANAGER"
	bl_idname = "SUB_PT_ANIM_SELECTOR"
	bl_label = "Animation"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	def draw(self, context):
		self.layout.label(text="Animation choose:")
		col = self.layout.column()
		col.prop(context.scene.uiControlProps, "actionList")

"""
 OPERATORS
"""

class LoadTarkovModel(bpy.types.Operator):
	bl_idname = "pt.open_fbx_browser"
	bl_label = "Import Tarkov model(FBX)"
	
	filepath = bpy.props.StringProperty(subtype="FILE_PATH")

	def execute(self, context):
		KillUnusedItems()
		bpy.ops.import_scene.fbx(filepath=self.filepath)
		impObj = bpy.context.selected_objects[0]
		topObj = GetTopLevelParent(impObj)
		AddModelToList(topObj)

		bpy.context.scene.modelIdx = bpy.context.scene.models.find(topObj.name)
		UpdateAttachData()
		if bpy.context.scene.uiControlProps.disableLod1Mesh:
			HideInViewport(True)
			HideL63Objects()
		return {'FINISHED'}

	def invoke(self, context, event):
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}

class RotateXObj(bpy.types.Operator):
	bl_idname = "pt.rotate_x_obj"
	bl_label = ""

	def execute(self, context):
		idx = bpy.context.scene.modelIdx
		try:
			item = bpy.context.scene.models[idx]
		except IndexError:
			self.report({'INFO'}, "Nothing selected in the list")
			return{'CANCELLED'}
		impObjs = bpy.context.scene.models
		selected = bpy.context.scene.objects.get(impObjs[idx].name, None)
		deg = math.degrees(selected.rotation_euler[0])
		deg +=90
		deg %= 360
		selected.rotation_euler[0] = math.radians(deg)
		return {'FINISHED'}

class RotateYObj(bpy.types.Operator):
	bl_idname = "pt.rotate_y_obj"
	bl_label = ""

	def execute(self, context):
		idx = bpy.context.scene.modelIdx
		try:
			item = bpy.context.scene.models[idx]
		except IndexError:
			self.report({'INFO'}, "Nothing selected in the list")
			return{'CANCELLED'}
		impObjs = bpy.context.scene.models
		selected = bpy.context.scene.objects.get(impObjs[idx].name, None)
		deg = math.degrees(selected.rotation_euler[1])
		deg +=90
		deg %= 360
		selected.rotation_euler[1] = math.radians(deg)
		return {'FINISHED'}

class RotateZObj(bpy.types.Operator):
	bl_idname = "pt.rotate_z_obj"
	bl_label = ""

	def execute(self, context):
		idx = bpy.context.scene.modelIdx
		try:
			item = bpy.context.scene.models[idx]
		except IndexError:
			self.report({'INFO'}, "Nothing selected in the list")
			return{'CANCELLED'}
		impObjs = bpy.context.scene.models
		selected = bpy.context.scene.objects.get(impObjs[idx].name, None)
		deg = math.degrees(selected.rotation_euler[2])
		deg +=90
		deg %= 360
		selected.rotation_euler[2] = math.radians(deg)
		return {'FINISHED'}

class DeleteModel(bpy.types.Operator):
	bl_idname = "pt.delete_model"
	bl_label = ""

	def execute(self, context):
		# check if object is exist in model list
		if GetModelListActiveProp() == None:
			return{'CANCELLED'}
		# not allow to delete if mod is installed
		if not GetModelListActiveProp().installed:
			# update counter of total weapon type models in list
			if GetModelListActiveProp().modType == "weapon":
				bpy.context.scene.dataColl.weaponBodyCount-=1

			# kill objects in scene
			selected = bpy.context.scene.objects.get(GetModelListActiveProp().name, None)
			bpy.ops.object.select_all(action='DESELECT')
			SelectHierarchy(selected, True)
			bpy.ops.object.delete()
			# kill the model in the list
			bpy.context.scene.models.remove(bpy.context.scene.modelIdx)

			if bpy.context.scene.modelIdx == 0 and len(bpy.context.scene.models.keys()) == 0:
				bpy.context.scene.uiControlProps.enableAttachFunc = False
				bpy.context.scene.dataColl.activeModelName = ""
			else:
				bpy.context.scene.modelIdx = len(bpy.context.scene.models.keys()) - 1

			KillUnusedItems()
		else:
			SpawnMsgBox(500, "please uninstall this mod first and be sure there's no other mod(s) on it")
		return {'FINISHED'}

class InfoBoxSpawner(bpy.types.Operator):
	bl_idname = "pt.spawn_msg_box"
	bl_label = "remind message"

	def execute(self, context):
		return {'FINISHED'}

	def invoke(self, context, event):
		wm = context.window_manager
		return wm.invoke_popup(self, width=bpy.context.scene.uiControlProps.msgPopUpLen)

	def draw(self, context):
		layout = self.layout
		layout.label(text=bpy.context.scene.uiControlProps.msgContent)

class AttachMod(bpy.types.Operator):
	bl_idname = "pt.attach_mod"
	bl_label = "Attach"

	def execute(self, context):
		AttachModToWeapon()
		return {'FINISHED'}

class AddEmptyMaterial(bpy.types.Operator):
	bl_idname = "pt.add_new_material"
	bl_label = " Add "
	bl_description = "add new material and name after selected object"
	def execute(self, context):
		CreateEmptyMat()
		return {'FINISHED'}

class DeleteMaterial(bpy.types.Operator):
	bl_idname = "pt.delete_material"
	bl_label = " Del "
	bl_description = "delete selected material on this list"
	def execute(self, context):
		KillMat()
		return {'FINISHED'}

class SetMaterial(bpy.types.Operator):
	bl_idname = "pt.set_material"
	bl_label = "Generate material nodes"
	bl_description = "generate material for selected object"

	def execute(self, context):
		GenerateMat()
		return {'FINISHED'}

class AttachToPrevSlot(bpy.types.Operator):
	bl_idname = "pt.attach_prev_mod_slot"
	bl_label = "prev"
	bl_description = "make selected mod attach to previous mod slot"

	def execute(self, context):
		RenewTheSlot(-1)
		return {'FINISHED'}

class AttachToNextSlot(bpy.types.Operator):
	bl_idname = "pt.attach_next_mod_slot"
	bl_label = "next"
	bl_description = "make selected mod attach to next mod slot"

	def execute(self, context):
		RenewTheSlot(1)
		return {'FINISHED'}

"""
 Debug funcs
"""
def PrintModelParentChildRelation():
	mdl = GetModelListActiveProp()
	print("parent : " + mdl.parentModel)
	print("child :")
	for c in mdl.childModels:
		print(c.name)

class TestingOp(bpy.types.Operator):
	bl_idname = "pt.i_am_a_tester"
	bl_label = "TEST"
	bl_description = "a button for function testing"

	def execute(self, context):
		PrintModelParentChildRelation()
		return {'FINISHED'}

classes = (
	#Properties
	UIControlProps, ShaderNodeDeployed, TexturePathInfo, MaterialListOfModel, ChildMods, TarkovModelList, DataCollection,
	#UIs
	TarkovModelUIList, MaterialUIList, ImportedModelManagePanel, AttachSubPanel, AnimationSelectPanel, HideLodPanel, MaterialGeneratePanel,
	#Operators
	LoadTarkovModel, InfoBoxSpawner, AttachMod, SetMaterial, AttachToPrevSlot, AttachToNextSlot, RotateXObj, RotateYObj, RotateZObj,
	DeleteModel, AddEmptyMaterial, DeleteMaterial, TestingOp
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	Scene.dataColl = PointerProperty(type=DataCollection)
	Scene.uiControlProps = PointerProperty(type=UIControlProps)
	Scene.models = CollectionProperty(type=TarkovModelList)
	Scene.deployedNodes = CollectionProperty(type=ShaderNodeDeployed)
	Scene.modelIdx = IntProperty(update=OnClickModelListUpdate)
	Scene.texPathLabel = PointerProperty(type=TexturePathInfo)
	
def unregister():
	for cls in classes:
		bpy.utils.unregister_class(cls)
	del Scene.dataColl
	del Scene.uiControlProps
	del Scene.models
	del Scene.deployedNodes
	del Scene.modelIdx
	del Scene.texPathLabel

if __name__ == "__main__":
	register()
