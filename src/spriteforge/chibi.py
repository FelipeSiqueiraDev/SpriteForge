"""Articulated chibi study derived from the approved three-view concept.

Geometry, not the generated turnaround, supplies the animation frames. Screen
directions are independently rendered through the CRONA camera and depth buffer.
"""
from __future__ import annotations

import math
import numpy as np

MODEL = "chibi-v3"
LEG_LENGTH = 10.0
ARM_LENGTH = 6.8
STRIDE = 16.8
FOOT_OFFSET = (0.0, 2.4, -4.4)
# Height, half-width, depth. The lower face is tapered; the forehead has volume.
HEAD_RINGS = (
    (42.0, 2.4, 2.8), (43.3, 5.2, 4.7), (45.3, 7.9, 6.5),
    (47.8, 10.2, 7.9), (51.5, 11.0, 8.5), (55.2, 11.1, 8.7),
    (58.6, 9.9, 8.1), (61.2, 7.3, 6.6), (63.1, 3.0, 3.2),
    (63.5, .12, .12),
)


def bend_joint(a, b, length, bend_direction):
    """Two bones with fixed length; projection defines their bend plane."""
    a, b = np.array(a, dtype=float), np.array(b, dtype=float)
    delta = b-a
    distance = float(np.linalg.norm(delta))
    if not 0 < distance <= 2*length:
        raise ValueError("Chibi limb target is out of reach")
    axis = delta/distance
    bend = np.array(bend_direction, dtype=float)
    bend -= axis*float(bend@axis)
    bend /= np.linalg.norm(bend)
    return a+delta/2+bend*math.sqrt(length*length-distance*distance/4)


def pose(action, index):
    from .core import ValidationError
    count = 4 if action == "idle" else 6 if action == "walk" else 0
    if type(index) is not int or not 0 <= index < count:
        raise ValidationError("Pose chibi inválida")
    phase = index/count
    bob = .12*math.sin(phase*math.tau) if action == "idle" else (0, -.55, .30)[index%3]
    joints = {"hips": [0, 0, 23+bob], "chest": [0, 0, 31.5+bob],
              "neck": [0, 0, 39.3+bob], "head": [0, 0, 52+bob]}
    contacts, feet = {}, {}
    for side, sign, offset in (("left", -1, 0), ("right", 1, .5)):
        p = (phase+offset)%1
        if action == "idle":
            step, lift = 0., 0.
        elif p <= .5:
            # In stance, foot + root travel stays fixed in world space.
            step, lift = STRIDE/4-STRIDE*p, 0.
        else:
            u = (p-.5)*2
            step = -STRIDE/4+(STRIDE/2)*(u*u*(3-2*u))
            lift = 3.4*math.sin(math.pi*u)
        hip = [sign*4.5, 0., 23+bob]
        ankle = [sign*4.5, step, 4.4+lift]
        knee = bend_joint(hip, ankle, LEG_LENGTH, [0, 1, 0])
        shoulder = [sign*8.6, 0, 35.4+bob]
        wrist = [sign*11.2, -step*.53, 23.0+bob]
        elbow = bend_joint(shoulder, wrist, ARM_LENGTH, [sign*.25, 1, 0])
        for joint, value in (("hip",hip),("knee",knee),("ankle",ankle),
                             ("shoulder",shoulder),("elbow",elbow),("wrist",wrist)):
            joints[side+"_"+joint] = np.asarray(value).tolist()
        contacts[side] = lift < 1e-8
        feet[side] = (np.asarray(ankle)+FOOT_OFFSET).tolist()
    return {"joints": joints, "contacts": contacts, "bob": bob,
            "feet": feet, "gait_phase": phase}


def head_y(x, z):
    """Front of the shaped head, used by the fitted facial decals."""
    heights = [r[0] for r in HEAD_RINGS]
    rx = float(np.interp(z, heights, [r[1] for r in HEAD_RINGS]))
    ry = float(np.interp(z, heights, [r[2] for r in HEAD_RINGS]))
    return ry*max(0, 1-(abs(x)/max(rx,.01))**3.5)**(1/3.5)


def head(scene, color, bob):
    segments = 24
    points = []
    for z, rx, ry in HEAD_RINGS:
        row = []
        for n in range(segments):
            theta = n*math.tau/segments
            x = rx*math.cos(theta)
            if math.sin(theta) >= 0:
                y = head_y(x,z)
            else:
                y = ry*math.sin(theta)
            row.append([x,y,z+bob])
        points.append(row)
    vertices = np.asarray(points).reshape(-1,3)
    normals = np.zeros_like(vertices)
    faces = []
    for row in range(len(points)-1):
        for col in range(segments):
            a=row*segments+col; b=row*segments+(col+1)%segments
            c=b+segments; d=a+segments
            for face in ((a,b,c),(a,c,d)):
                faces.append(face)
                normal=np.cross(vertices[face[1]]-vertices[face[0]],vertices[face[2]]-vertices[face[0]])
                for vertex in face:
                    normals[vertex]+=normal
    normals /= np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-8)
    for face in faces:
        scene.triangle(vertices[list(face)], color, "body", normals[list(face)])


def face_polygon(scene, points, color, bob, offset=.16, part="body"):
    # Triangulate a convex, gently curved patch sitting on the head surface.
    center=np.mean(points,axis=0)
    fit=lambda p: [p[0],head_y(p[0],p[1])+offset,p[1]+bob]
    for a,b in zip(points,points[1:]+points[:1]):
        vertices=[fit(center),fit(a),fit(b)]
        normal=np.cross(np.asarray(vertices[1])-vertices[0],np.asarray(vertices[2])-vertices[0])
        if normal[1] < 0:
            vertices=[vertices[0],vertices[2],vertices[1]]
        scene.triangle(vertices,color,part,[[0,1,0]]*3)


def patch(scene,x,z,w,h,color,bob,offset=.16,part="body"):
    face_polygon(scene,[(x-w/2,z-h/2),(x+w/2,z-h/2),(x+w/2,z+h/2),(x-w/2,z+h/2)],color,bob,offset,part)


def collar(scene, color, bob):
    for n in range(16):
        a,b=n*math.tau/16,(n+1)*math.tau/16
        scene.bone((3.5*math.cos(a),3.1*math.sin(a),38.6+bob),
                   (3.5*math.cos(b),3.1*math.sin(b),38.6+bob),.48,color,"shirt")


def sweatshirt(scene,color,bob):
    """A tailored, rounded torso rather than an ellipsoidal belly."""
    rings=((24.2,7.8,4.8),(25.5,8.3,5.0),(29,8.7,5.2),
           (33,9.0,5.3),(36.2,8.4,4.8),(38.1,3.7,3.0))
    vertices=[];segments=16
    for z,rx,ry in rings:
        for n in range(segments):
            a=n*math.tau/segments
            vertices.append([rx*math.copysign(abs(math.cos(a))**.8,math.cos(a)),
                             ry*math.copysign(abs(math.sin(a))**.8,math.sin(a)),z+bob])
    vertices=np.asarray(vertices);normals=np.zeros_like(vertices);faces=[]
    for row in range(len(rings)-1):
        for n in range(segments):
            a=row*segments+n;b=row*segments+(n+1)%segments;c=b+segments;d=a+segments
            for f in ((a,b,c),(a,c,d)):
                faces.append(f)
                normal=np.cross(vertices[f[1]]-vertices[f[0]],vertices[f[2]]-vertices[f[0]])
                for v in f:normals[v]+=normal
    normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-8)
    for f in faces:scene.triangle(vertices[list(f)],color,'shirt',normals[list(f)])


def soft_foot(scene,center,radii,color,part):
    center=np.asarray(center);rx,ry,rz=radii
    ring=np.array([(-.75,-1),(.75,-1),(1,-.6),(1,.65),(.75,1),(-.75,1),(-1,.65),(-1,-.6)])
    points=[]
    for scale,height in ((1.,-1.),(1.,-.65),(.8,.65)):
        for x,y in ring:
            z=rz*height if height<0 else rz*(height-.45*max(0,y))
            points.append(center+[x*rx*scale,y*ry*scale,z])
    points.extend((center+[0,0,rz*.75],center+[0,0,-rz]))
    vertices=np.asarray(points);normals=np.zeros_like(vertices);faces=[]
    for n in range(8):
        nxt=(n+1)%8
        faces.extend(((25,nxt,n),(24,n+16,nxt+16)))
        for row in range(2):
            a=row*8+n;b=row*8+nxt;c=b+8;d=a+8
            faces.extend(((a,b,c),(a,c,d)))
    for f in faces:
        normal=np.cross(vertices[f[1]]-vertices[f[0]],vertices[f[2]]-vertices[f[0]])
        for v in f:normals[v]+=normal
    normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-8)
    for f in faces:scene.triangle(vertices[list(f)],color,part,normals[list(f)])


def build_scene(recipe,current):
    from .rig import Scene
    scene=Scene(); scene.ambient=.4; scene.cull_smooth_backfaces=True
    joints=current["joints"]; bob=current["bob"]
    skin=recipe["body_color"]; outfit=recipe.get("outfit") or {}
    # Torso and pelvis stay beneath the removable clothes.
    scene.ellipsoid((0,0,24+bob),(7.0,4.3,4.4),skin)
    scene.ellipsoid((0,0,31.5+bob),(8.4,4.9,7.2),skin)
    scene.ellipsoid((0,0,41.0+bob),(2.8,2.7,3.0),skin)
    head(scene,skin,bob)
    for sign in (-1,1):
        scene.ellipsoid((sign*10.8,0,52.2+bob),(1.35,1.35,1.9),skin)
        scene.ellipsoid((sign*11.5,.7,52.2+bob),(.4,.4,1.0),"#ba795c")
        x=sign*3.8
        # Sclera, dark upper eyelid, iris and a small highlight; all rotate in 3D.
        eye=[(x-2.3,52.7),(x-2.1,55.2),(x-.5,55.8),(x+2.0,55.2),
             (x+2.2,52.8),(x+.9,52.2),(x-1.2,52.2)]
        face_polygon(scene,eye,"#493025",bob)
        eye_y=head_y(x,54)+.15
        scene.ellipsoid((x,eye_y,54+bob),(1.95,.80,1.65),"#f1dec1",rings=4,segments=8)
        scene.ellipsoid((x,eye_y+.95,54+bob),(1.25,.25,1.45),"#593b2c",rings=4,segments=8)
        scene.ellipsoid((x,eye_y+1.20,54.1+bob),(.65,.18,1.15),"#30251f",rings=4,segments=8)
        scene.ellipsoid((x-.45,eye_y+1.40,54.8+bob),(.36,.12,.36),"#fff0d7",rings=3,segments=6)
        face_polygon(scene,[(x-1.8,53.0),(x-1.6,54.7),(x,55.0),
                            (x+1.7,54.6),(x+1.7,53.0),(x,52.7)],"#f1dec1",bob,.25)
        patch(scene,x,54.0,2.4,2.7,"#593b2c",bob,.34)
        patch(scene,x,54.2,1.25,2.4,"#30251f",bob,.43)
        patch(scene,x-.5,54.9,.65,.65,"#fff0d7",bob,.52)
        brow=[(x-2.2,57.0),(x+2.2,56.8),(x+1.7,57.9),(x-1.4,58.0)]
        face_polygon(scene,brow,recipe.get("hair") or "#63402e",bob,.19)
    scene.ellipsoid((0,8.5,50.1+bob),(.8,.9,.75),skin)
    patch(scene,0,47.3,2.0,.45,"#a76c52",bob,.25)
    for side in ("left","right"):
        p=lambda joint:np.asarray(joints[side+"_"+joint])
        scene.bone(p("hip"),p("knee"),3.2,skin)
        scene.bone(p("knee"),p("ankle"),2.8,skin)
        scene.ellipsoid(p("knee"),(3.2,3.2,3.2),skin)
        foot=p("ankle")+(0,2.4,-2.1)
        soft_foot(scene,foot,(3.2,4.8,2.3),skin,'body')
        scene.bone(p("shoulder"),p("elbow"),2.9,skin)
        scene.bone(p("elbow"),p("wrist"),2.35,skin)
        scene.ellipsoid(p("elbow"),(2.9,2.9,2.9),skin)
        hand=p("wrist")+(0,.2,-1.1)
        scene.ellipsoid(hand,(2.3,1.9,2.8),skin)
        sign=-1 if side=="left" else 1
        scene.ellipsoid(hand+(-sign*1.9,1,.3),(.9,.9,1.4),skin)
        if "shirt" in outfit:
            c=outfit["shirt"]
            scene.bone(p("shoulder"),p("elbow"),3.45,c,"shirt")
            scene.ellipsoid(p("elbow"),(3.6,3.5,3.8),c,"shirt")
            cuff=p("wrist")+(0,0,.8)
            scene.bone(p("elbow"),cuff,3.05,c,"shirt")
            scene.ellipsoid(cuff,(3.1,2.85,1.2),c,"shirt")
        if "trousers" in outfit:
            c=outfit["trousers"]
            scene.bone(p("hip"),p("knee"),3.7,c,"trousers")
            scene.ellipsoid(p("knee"),(3.8,3.7,3.5),c,"trousers")
            cuff=p("ankle")+(0,0,1.7)
            scene.bone(p("knee"),cuff,3.25,c,"trousers")
            scene.ellipsoid(cuff,(3.4,3.15,1.3),c,"trousers")
        if "boots" in outfit:
            c=outfit["boots"]
            soft_foot(scene,foot,(3.5,5.1,2.3),c,'boots')
            scene.ellipsoid(p("ankle")+(0,0,.8),(3.25,3.2,2.5),c,"boots")
            scene.foot(foot+(0,0,-1.8),(3.6,5.2,.5),"#493429","boots")
    if "trousers" in outfit:
        scene.ellipsoid((0,0,23.5+bob),(7.5,4.8,4.7),outfit["trousers"],"trousers")
    if "shirt" in outfit:
        c=outfit["shirt"]
        sweatshirt(scene,c,bob)
        scene.ellipsoid((0,0,24.1+bob),(8.2,5.2,1.45),c,"shirt")
        collar(scene,c,bob)
    if recipe.get("hair"):
        scene.ellipsoid((0,-.4,54.4+bob),(11.6,9.1,9.7),recipe["hair"],"hair",upper_only=True)
    if recipe.get("beard"):
        face_polygon(scene,[(-5.4,49.2),(-4.4,46.6),(0,44.1),(4.4,46.6),(5.4,49.2),
                            (2.6,48.7),(0,46.4),(-2.6,48.7)],recipe["beard"],bob,.65,"beard")
    if recipe.get("glasses"):
        c=recipe["glasses"]
        for x in (-3.4,3.4):
            for z in (51.8,56.1):
                patch(scene,x,z,5.3,.5,c,bob,1.65,"glasses")
            for edge in (-2.6,2.6):
                patch(scene,x+edge,54.0,.5,4.7,c,bob,1.65,"glasses")
        patch(scene,0,54.4,1.6,.5,c,bob,1.65,"glasses")
        for sign in (-1,1):
            scene.bone((sign*6,head_y(sign*6,54.4)+.7,54.4+bob),
                       (sign*10.1,0,54.4+bob),.3,c,"glasses")
    if recipe.get("scar"):
        face_polygon(scene,[(6.6,49.3),(7.1,49.3),(6.3,51.2),(5.9,51.2)],recipe["scar"],bob,.8,"scar")
    return scene
