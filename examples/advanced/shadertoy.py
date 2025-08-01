import struct
import sys

import pygame
import zengl
import zengl_extras

zengl_extras.init()

pygame.init()
pygame.display.set_mode((1280, 720), flags=pygame.OPENGL | pygame.DOUBLEBUF, vsync=True)

window_size = pygame.display.get_window_size()
window_aspect = window_size[0] / window_size[1]

ctx = zengl.context()

image = ctx.image(window_size, 'rgba8unorm')
uniform_buffer = ctx.buffer(size=64)

# Tested with:
# Happy Jumping - https://www.shadertoy.com/view/3lsSzf
# Raymarching - Primitives - https://www.shadertoy.com/view/Xds3zN
# GLSL ray tracing test - https://www.shadertoy.com/view/3sc3z4
# Ray Marching: Part 6 - https://www.shadertoy.com/view/4tcGDr
# Seascape - https://www.shadertoy.com/view/Ms2SD1
# Mandelbulb - https://www.shadertoy.com/view/MdXSWn

# Paste your code below

shadertoy = '''
void mainImage( out vec4 fragColor, in vec2 fragCoord )
{
    // Normalized pixel coordinates (from 0 to 1)
    vec2 uv = fragCoord/iResolution.xy;

    // Time varying pixel color
    vec3 col = 0.5 + 0.5*cos(iTime+uv.xyx+vec3(0,2,4));

    // Output to screen
    fragColor = vec4(col,1.0);
}
'''

ctx.includes['shadertoy'] = shadertoy
ctx.includes['uniforms'] = '''
    layout (std140) uniform Uniforms {
        vec3 iResolution;
        float iTime;
        float iTimeDelta;
        int iFrame;
        vec4 iMouse;
        vec4 iDate;
    };
'''

canvas = ctx.pipeline(
    vertex_shader='''
        #version 300 es
        precision highp float;

        vec2 positions[3] = vec2[](
            vec2(-1.0, -1.0),
            vec2(3.0, -1.0),
            vec2(-1.0, 3.0)
        );

        void main() {
            gl_Position = vec4(positions[gl_VertexID], 0.0, 1.0);
        }
    ''',
    fragment_shader='''
        #version 300 es
        precision highp float;

        #include "uniforms"
        #include "shadertoy"

        layout (location = 0) out vec4 shader_color_output;

        void main() {
            mainImage(shader_color_output, gl_FragCoord.xy);
        }
    ''',
    layout=[
        {
            'name': 'Uniforms',
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
    framebuffer=[image],
    topology='triangles',
    vertex_count=3,
)

ubo = struct.Struct('=3f1f1f1i8x4f4f')
last_time = 0.0
frame = 0

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

    mouse_pos = pygame.mouse.get_pos()
    now  = pygame.time.get_ticks() / 1000.0

    ctx.new_frame()
    image.clear()
    uniform_buffer.write(ubo.pack(
        window_size[0], window_size[1], 0.0,
        now,
        now - last_time,
        frame,
        mouse_pos[0], mouse_pos[1], 0.0, 0.0,
        0.0, 0.0, 0.0, 0.0,
    ))
    canvas.render()
    image.blit()
    ctx.end_frame()
    frame += 1

    pygame.display.flip()
