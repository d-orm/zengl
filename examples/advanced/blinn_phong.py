import struct
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

uniform_buffer = ctx.buffer(size=80)
material_uniform_buffer = ctx.buffer(size=112)

pipeline = ctx.pipeline(
    vertex_shader='''
        #version 300 es
        precision highp float;

        layout (std140) uniform Common {
            mat4 mvp;
            vec4 eye_pos;
        };

        layout (location = 0) in vec3 in_vertex;
        layout (location = 1) in vec3 in_normal;

        out vec3 v_vertex;
        out vec3 v_normal;

        void main() {
            v_vertex = in_vertex;
            v_normal = in_normal;
            gl_Position = mvp * vec4(v_vertex, 1.0);
        }
    ''',
    fragment_shader='''
        #version 300 es
        precision highp float;

        layout (std140) uniform Common {
            mat4 mvp;
            vec4 eye_pos;
        };

        layout (std140) uniform Material {
            vec4 light_pos;
            vec4 light_color;
            float light_power;
            vec4 ambient_color;
            vec4 diffuse_color;
            vec4 spec_color;
            float shininess;
        };

        in vec3 v_vertex;
        in vec3 v_normal;

        layout (location = 0) out vec4 out_color;

        const float screen_gamma = 2.2;

        void main() {
            vec3 light_dir = light_pos.xyz - v_vertex;
            float light_distance = length(light_dir);
            light_distance = light_distance * light_distance;
            light_dir = normalize(light_dir);

            float lambertian = max(dot(light_dir, v_normal), 0.0);
            float specular = 0.0;

            if (lambertian > 0.0) {
                vec3 view_dir = normalize(eye_pos.xyz - v_vertex);
                vec3 half_dir = normalize(light_dir + view_dir);
                float spec_angle = max(dot(half_dir, v_normal), 0.0);
                specular = pow(spec_angle, shininess);
            }

            vec3 color_linear = ambient_color.rgb +
                diffuse_color.rgb * lambertian * light_color.rgb * light_power / light_distance +
                spec_color.rgb * specular * light_color.rgb * light_power / light_distance;

            vec3 color_gamma_corrected = pow(color_linear, vec3(1.0 / screen_gamma));
            out_color = vec4(color_gamma_corrected, 1.0);
        }
    ''',
    layout=[
        {
            'name': 'Common',
            'binding': 0,
        },
        {
            'name': 'Material',
            'binding': 1,
        },
    ],
    resources=[
        {
            'type': 'uniform_buffer',
            'binding': 0,
            'buffer': uniform_buffer,
        },
        {
            'type': 'uniform_buffer',
            'binding': 1,
            'buffer': material_uniform_buffer,
            'offset': 0,
            'size': 112,
        },
    ],
    framebuffer=[image, depth],
    topology='triangles',
    cull_face='back',
    vertex_buffers=zengl.bind(vertex_buffer, '3f 3f', 0, 1),
    vertex_count=vertex_buffer.size // zengl.calcsize('3f 3f'),
)

light_pos = (2.0, 3.0, 4.0)
light_color = (1.0, 1.0, 1.0)
light_power = 40.0
ambient_color = (0.0, 0.01, 0.05)
diffuse_color = (0.0, 0.1, 0.5)
spec_color = (1.0, 1.0, 1.0)
shininess = 16.0

material_uniform_buffer.write(struct.pack(
    '=3f4x3f4xf12x3f4x3f4x3f4xf12x',
    *light_pos, *light_color, light_power,
    *ambient_color, *diffuse_color, *spec_color,
    shininess,
))

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    now = pygame.time.get_ticks() / 1000.0

    ctx.new_frame()
    x, y = np.cos(now * 0.5) * 5.0, np.sin(now * 0.5) * 5.0
    camera = zengl.camera((x, y, 2.0), (0.0, 0.0, 0.0), aspect=window_aspect, fov=45.0)
    uniform_buffer.write(camera + struct.pack('=3f4x', x, y, 2.0))

    image.clear()
    depth.clear()
    pipeline.render()
    image.blit()
    ctx.end_frame()

    pygame.display.flip()
