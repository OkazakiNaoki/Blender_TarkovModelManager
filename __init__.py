bl_info = {
	"name": "Tarkov models manager",
	"author": "Yu Hsuan Hung (Okazaki Naoki)",
	"version": (1, 0),
	"blender": (2, 80, 0),
	"location": "View3D > SidePanel(name: TMM)",
	"description": "Manage imported Tarkov models and allow you to attach them via UI. Also allow you to generate PBR material to preview the entire model.",
	"warning": "",
	"doc_url": "",
	"category": "Object",
}

import bpy
import os

from . import TMM

def register():
	TMM.register()


def unregister():
	TMM.unregister()


if __name__ == "__main__":
	register()