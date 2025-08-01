import sys

import assets
import numpy as np
import pygame
import zengl
import zengl_extras
from objloader import Obj

zengl_extras.init()

pygame.init()
pygame.display.set_mode((1280, 720), flags=pygame.OPENGL | pygame.DOUBLEBUF, vsync=True)

window_size = pygame.display.get_window_size()
window_aspect = window_size[0] / window_size[1]

ctx = zengl.context()

image = ctx.image(window_size, 'rgba8unorm', samples=4)
depth = ctx.image(window_size, 'depth24plus', samples=4)
image.clear_value = (0.2, 0.2, 0.2, 1.0)

model = Obj.open(assets.get('blob.obj')).pack('vx vy vz nx ny nz')
vertex_buffer = ctx.buffer(model)

uniform_buffer = ctx.buffer(size=64)

pipeline = ctx.pipeline(
    vertex_shader='''
        #version 300 es
        precision highp float;

        layout (std140) uniform Common {
            mat4 mvp;
        };

        layout (location = 0) in vec3 in_vert;
        layout (location = 1) in vec3 in_norm;

        out vec3 v_norm;

        void main() {
            gl_Position = mvp * vec4(in_vert, 1.0);
            v_norm = in_norm;
        }
    ''',
    fragment_shader='''
        #version 300 es
        precision highp float;

        in vec3 v_norm;

        layout (location = 0) out vec4 out_color;

        void main() {
            vec3 light = vec3(4.0, 3.0, 10.0);
            float lum = dot(normalize(light), normalize(v_norm)) * 0.5 + 0.5;
            out_color = vec4(lum, lum, lum, 1.0);
        }
    ''',
    layout=[
        {
            'name': 'Common',
            'binding': 0,
        },
    ],
    resources=[
        {
            'type': 'uniform_buffer',
            'binding': 0,
            'buffer': uniform_buffer,
        },
    ],
    framebuffer=[image, depth],
    topology='triangles',
    cull_face='back',
    vertex_buffers=zengl.bind(vertex_buffer, '3f 3f', 0, 1),
    vertex_count=vertex_buffer.size // zengl.calcsize('3f 3f'),
)

temp_buffer = ctx.buffer(np.array([
    [0.00, 0.00, 0.0], [0.00, 0.00, 0.1],
    [0.25, 0.00, 0.0], [0.25, 0.00, 0.1],
    [0.50, 0.00, 0.0], [0.50, 0.00, 0.1],
    [0.75, 0.00, 0.0], [0.75, 0.00, 0.1],
    [1.00, 0.00, 0.0], [1.00, 0.00, 0.1],
    [0.00, 0.25, 0.0], [0.00, 0.25, 0.1],
    [0.25, 0.25, 0.0], [0.25, 0.25, 0.1],
    [0.50, 0.25, 0.0], [0.50, 0.25, 0.1],
    [0.75, 0.25, 0.0], [0.75, 0.25, 0.1],
    [0.00, 0.50, 0.0], [0.00, 0.50, 0.1],
    [0.25, 0.50, 0.0], [0.25, 0.50, 0.1],
    [0.50, 0.50, 0.0], [0.50, 0.50, 0.1],
    [0.00, 0.75, 0.0], [0.00, 0.75, 0.1],
    [0.25, 0.75, 0.0], [0.25, 0.75, 0.1],
    [0.00, 1.00, 0.0], [0.00, 1.00, 0.1],
], 'f4').tobytes())

vertex_count = vertex_buffer.size // zengl.calcsize('3f 3f')
index_buffer = ctx.buffer(np.array([
    np.arange(0, vertex_count, 3),
    np.arange(1, vertex_count, 3),
    np.arange(2, vertex_count, 3),
    np.full(vertex_count // 3, -1),
], dtype='i4').T.tobytes())

wireframe = ctx.pipeline(
    vertex_shader='''
        #version 300 es
        precision highp float;

        layout (std140) uniform Common {
            mat4 mvp;
        };

        layout (location = 0) in vec3 in_vert;

        void main() {
            gl_Position = mvp * vec4(in_vert, 1.0);
        }
    ''',
    fragment_shader='''
        #version 300 es
        precision highp float;

        layout (location = 0) out vec4 out_color;

        void main() {
            gl_FragDepth = gl_FragCoord.z - 1e-4;
            out_color = vec4(0.0, 0.0, 0.0, 1.0);
        }
    ''',
    layout=[
        {
            'name': 'Common',
            'binding': 0,
        },
    ],
    resources=[
        {
            'type': 'uniform_buffer',
            'binding': 0,
            'buffer': uniform_buffer,
        },
    ],
    framebuffer=[image, depth],
    topology='line_loop',
    vertex_buffers=zengl.bind(vertex_buffer, '3f 3f', 0, -1),
    index_buffer=index_buffer,
    vertex_count=index_buffer.size // 4,
)

normals = ctx.pipeline(
    vertex_shader='''
        #version 300 es
        precision highp float;

        layout (std140) uniform Common {
            mat4 mvp;
        };

        layout (location = 0) in vec3 in_point;

        layout (location = 1) in vec3 in_vert_0;
        layout (location = 2) in vec3 in_norm_0;
        layout (location = 3) in vec3 in_vert_1;
        layout (location = 4) in vec3 in_norm_1;
        layout (location = 5) in vec3 in_vert_2;
        layout (location = 6) in vec3 in_norm_2;

        void main() {
            vec3 vert = in_vert_0 + (in_vert_1 - in_vert_0) * in_point.x + (in_vert_2 - in_vert_0) * in_point.y;
            vec3 norm = in_norm_0 + (in_norm_1 - in_norm_0) * in_point.x + (in_norm_2 - in_norm_0) * in_point.y;
            gl_Position = mvp * vec4(vert + normalize(norm) * in_point.z, 1.0);
        }
    ''',
    fragment_shader='''
        #version 300 es
        precision highp float;

        layout (location = 0) out vec4 out_color;

        void main() {
            out_color = vec4(0.0, 0.0, 0.0, 1.0);
        }
    ''',
    layout=[
        {
            'name': 'Common',
            'binding': 0,
        },
    ],
    resources=[
        {
            'type': 'uniform_buffer',
            'binding': 0,
            'buffer': uniform_buffer,
        },
    ],
    framebuffer=[image, depth],
    topology='lines',
    vertex_buffers=[
        *zengl.bind(temp_buffer, '3f', 0),
        *zengl.bind(vertex_buffer, '3f 3f 3f 3f 3f 3f /i', 1, 2, 3, 4, 5, 6),
    ],
    vertex_count=temp_buffer.size // zengl.calcsize('3f'),
    instance_count=vertex_buffer.size // zengl.calcsize('3f 3f 3f 3f 3f 3f'),
)

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    now = pygame.time.get_ticks() / 1000.0

    ctx.new_frame()
    x, y = np.cos(now * 0.5) * 5.0, np.sin(now * 0.5) * 5.0
    camera = zengl.camera((x, y, 2.0), (0.0, 0.0, 0.0), aspect=window_aspect, fov=45.0)
    uniform_buffer.write(camera)

    image.clear()
    depth.clear()
    pipeline.render()
    wireframe.render()
    normals.render()
    image.blit()
    ctx.end_frame()

    pygame.display.flip()
