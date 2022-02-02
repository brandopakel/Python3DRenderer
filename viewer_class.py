from OpenGL import *
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import numpy
import random

class Viewer(object):
    def __init__(self):
        """Initialize the viewer"""
        self.init_interface()
        self.init_opengl()
        self.init_scene()
        self.init_interaction()
        init_primitives()
    
    def init_interface(self):
        """"initializes the window and register the render function"""
        glutInit()
        glutInitWindowSize(640,480)
        glutCreateWindow("3D Modeller")
        glutInitDisplayMode(GLUT_SINGLE | GLUT_RGB)
        glutDisplayFunc(self.render)
    
    def init_opengl(self):
        """initialize the opengl settings to render the scene"""
        self.inverseModelView = numpy.identity(4)
        self.modelView = numpy.identity(4)

        glEnable(GL_CULL_FACE)
        glCullFace(GL_BACK)
        glEnable(GL_DEPTH_TEST)
        glDepthFunc(GL_LESS)

        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_POSITION, GLfloat_4(0,0,1,0))
        glLightfv(GL_LIGHT0, GL_SPOT_DIRECTION, GLfloat_3(0,0,-1))

        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glEnable(GL_COLOR_MATERIAL)
        glClearColor(0.4,0.4,0.4,0.0)
    
    def init_scene(self):
        """intialize the scene object and initial scene"""
        self.scene = Scene()
        self.create_sample_scene()
    
    def create_sample_scene(self):
        cube_node = Cube()
        cube_node.translate(2,0,2)
        cube_node.color_index = 2
        self.scene.add_node(cube_node)

        sphere_node = Sphere()
        sphere_node.translate(-2,0,2)
        sphere_node.color_index = 3
        self.scene.add_node(sphere_node)

        hierarchical_node = SnowFigure()
        hierarchical_node.translate(-2,0,2)
        self.scene.add_node(hierarchical_node)
    
    def init_interaction(self):
        """init user interaction and callbacks"""
        self.interaction = Interaction()
        self.interaction.register_callback('pick', self.pick)
        self.interaction.register_callback('move', self.move)
        self.interaction.register_callback('place', self.place)
        self.interaction.register_callback('rotate_color', self.rotate_color)
        self.interaction.register_callback('scale', self.scale)
    
    def render(self):
        """the render pass for the scene"""
        self.init_view()

        glEnable(GL_LIGHTING)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        #load the modelview matrix from the current state of the trackball
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        loc = self.interaction.translation
        glTranslated(loc[0],loc[1],loc[2])
        glMultMatrixf(self.interaction.trackball.matrix)

        #store the inverse of the current model view
        currentModelView = numpy.array(glGetFloatv(GL_MODELVIEW_MATRIX))
        self.modelView = numpy.transpose(currentModelView)
        self.inverseModelView = numpy.linalg.inv(numpy.transpose(currentModelView))

        #render the scene. this will call the render function for each object in the scene
        self.scene.render()

        #draw the grid
        glDisable(GL_LIGHTING)
        glCallList(GL_OBJECT_PLANE)
        glPopMatrix()

        #flush the buffers so that the scene can be drawn
        glFlush()
    
    def init_view(self):
        """initialize the projection matrix"""
        xSize, ySize = glutGet(GLUT_WINDOW_WIDTH), glutGet(GLUT_WINDOW_HEIGHT)
        aspect_ratio = float(xSize) / float(ySize)

        #load the projection matrix. always the same
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

        glViewport(0,0,xSize,ySize)
        gluPerspective(70,aspect_ratio,0.1,1000.0)
        glTranslated(0,0,-15)

    def main_loop(self):
        glutMainLoop()

class Scene(object):
    PLACE_DEPTH = 15.0

    def __init__(self):
        self.node_list = list()
        self.selected_node = None
    
    def add_node(self,node):
        """Add a new node to the scene"""
        self.node_list.append(node)
    
    def render(self):
        """Render the scene"""
        for node in self.node_list:
            node.render()

class Node(object):
    """Base class for scene elements"""
    def __init__(self):
        self.color_index = random.randint(color.MIN_COLOR, color.MAX_COLOR)
        self.aabb = AABB([0.0,0.0,0.0],[0.5,0.5,0.5])
        self.translation_matrix = numpy.identity(4)
        self.scaling_matrix = numpy.identity(4)
        self.selected = False
    
    def render(self):
        """Renders items to the screen"""
        glPushMatrix()
        glMultMatrixf(numpy.transpose(self.translation_matrix))
        glMultMatrixf(self.scaling_matrix)
        cur_color = color.COLORS[self.color_index]
        glColor3f(cur_color[0],cur_color[1],cur_color[2])
        if self.selected:
            glMaterialfv(GL_FRONT, GL_EMISSION, [0.3,0.3,0.3])
        
        self.render_self()

        if self.selected:
            glMaterialfv(GL_FRONT,GL_EMISSION,[0.0,0.0,0.0])
        glPopMatrix()

    def render_self(self):
        raise NotImplementedError("The Abstract Node Class doesn't define 'render_self'")
    
class Primitive(Node):
    def __init__(self):
        super(Primitive,self).__init__
        self.call_list = None
    
    def render_self(self):
        glCallList(self.call_list)

class Sphere(Primitive):
    """Sphere primitive"""
    def __init__(self):
        super(Sphere, self).__init__()
        self.call_list = G_OBJ_SPHERE

class Cube(Primitive):
    """Cube primitive"""
    def __init__(self):
        super(Cube, self).__init__()
        self.call_list = G_OBJ_CUBE

class Interaction(object):
    def __init__(self):
        """Handles user interaction"""
        self.pressed = None
        self.translation = [0,0,0,0]
        self.trackball = trackball.Trackball(theta = -25, distance = 15)
        self.mouse_loc = None
        self.callbacks = defaultdict(list)

        self.register()
    
    def register(self):
        """Registers callbacks with glut"""
        glutMouseFunc(self.handle_mouse_button)
        glutMotionFunc(self.handle_mouse_move)
        glutKeyboardFunc(self.handle_keystroke)
        glutSpecialFunc(self.handle_keystroke)

    def translate(self,x,y,z):
        """translate the camera"""
        self.translation[0] += x
        self.translation[1] += y
        self.translation[2] += z
    
    def handle_mouse_button(self,button,mode,x,y):
        """Called when the mouse button is pressed or released"""
        xSize, ySize = glutGet(GLUT_WINDOW_WIDTH), glutGet(GLUT_WINDOW_HEIGHT)
        y = ySize - y
        self.mouse_loc = (x,y)

        if mode == GLUT_DOWN:
            self.pressed = button
            if button == GLUT_RIGHT_BUTTON:
                pass
            elif button == GLUT_LEFT_BUTTON:
                self.trigger('pick',x,y)
            elif button == 3:
                self.translate(0,0,1.0)
            elif button == 4:
                self.translate(0,0,-1.0)
        else:
            self.pressed = None
        glutPostRedisplay()
    
    def handle_mouse_move(self,x,screen_y):
        """Called when the mouse is moved"""
        xSize, ySize = glutGet(GLUT_WINDOW_WIDTH), glutGet(GLUT_WINDOW_HEIGHT)
        y = ySize - screen_y
        if self.pressed is not None:
            dx = x - self.mouse_loc[0]
            dy = y - self.mouse_loc[1]
            if self.pressed == GLUT_RIGHT_BUTTON and self.trackball is not None:
                self.trackball.drag_to(self.mouse_loc[0], self.mouse_loc[1],dx,dy)
            elif self.pressed == GLUT_LEFT_BUTTON:
                self.trigger('move',x,y)
            elif self.pressed ==GLUT_MIDDLE_BUTTON:
                self.translate(dx/60.0,dy/60.0,0)
            else:
                pass
            glutPostRedisplay()
        self.mouse_loc = (x,y)

    def handle_keystroke(self,key,x,screen_y):
        """Called on keyboard input from the user"""
        xSize, ySize = glutGet(GLUT_WINDOW_WIDTH), glutGet(GLUT_WINDOW_HEIGHT)
        y = ySize - screen_y
        if key == 's':
            self.trigger('place', 'sphere', x, y)
        elif key == 'c':
            self.trigger('place', 'cube', x, y)
        elif key == GLUT_KEY_UP:
            self.trigger('scale', up=True)
        elif key == GLUT_KEY_DOWN:
            self.trigger('scale', up=False)
        elif key == GLUT_KEY_LEFT:
            self.trigger('rotate_color', forward=True)
        elif key == GLUT_KEY_RIGHT:
            self.trigger('rotate_color', forward=False)
        glutPostRedisplay()

    def register_callback(self, name, func):
        self.callbacks[name].append(func)
    
    def trigger(self,name,*args,**kwargs):
        for func in self.callbacks[name]:
            func(*args,**kwargs)

if __name__ == "__main__":
    viewer = Viewer()
    viewer.main_loop()