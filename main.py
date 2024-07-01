import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from PIL import Image
import numpy as np

# Define cube vertices and faces
vertices = np.array([
    (0, 0, 0),  # 0: bottom-left-front
    (1, 0, 0),  # 1: bottom-right-front
    (1, 1, 0),  # 2: top-right-front
    (0, 1, 0),  # 3: top-left-front
    (0, 0, 1),  # 4: bottom-left-back
    (1, 0, 1),  # 5: bottom-right-back
    (1, 1, 1),  # 6: top-right-back
    (0, 1, 1)   # 7: top-left-back
], dtype=np.float32)

faces = np.array([
    (0, 1, 2, 3),  # front face
    (4, 5, 6, 7),  # back face
    (3, 2, 6, 7),  # top face
    (0, 1, 5, 4),  # bottom face
    (1, 2, 6, 5),  # right face
    (0, 3, 7, 4)   # left face
], dtype=np.uint32)

# Texture coordinates for the faces
texture_coords = [
    (0, 0), (1, 0), (1, 1), (0, 1)  # For each face
]

textures = {}

def load_texture(filename):
    try:
        img = Image.open(filename)
        img = img.convert("RGBA")
        img_data = np.array(img).tobytes()
        texture_id = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texture_id)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.width, img.height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        print(f"Texture loaded: {filename} with ID {texture_id}")
        return texture_id
    except Exception as e:
        print(f"Failed to load texture {filename}: {e}")
        return None

def Cube(position, block_type, visible_faces):
    x, y, z = position
    block_textures = {
        'dirt': [textures['dirt']] * 6,
        'grass': [textures['grass_side'], textures['grass_side'], textures['grass_top'], textures['dirt'], textures['grass_side'], textures['grass_side']],
        'stone': [textures['stone']] * 6
    }
    textures_list = block_textures[block_type]

    for i, face in enumerate(faces):
        if visible_faces[i]:  # Only render the face if it's visible
            glBindTexture(GL_TEXTURE_2D, textures_list[i])
            glBegin(GL_QUADS)
            for j, vertex in enumerate(face):
                # Texture coordinates
                glTexCoord2f(*texture_coords[j])
                glVertex3f(vertices[vertex][0] + x, vertices[vertex][1] + y, vertices[vertex][2] + z)
            glEnd()

def generate_chunk(offset_x, offset_z, chunk_size=16):
    blocks = {}
    for x in range(chunk_size):
        for z in range(chunk_size):
            for y in range(-128, 1):  # Adjusting height range to 128 deep
                if y < -5:
                    block_type = 'stone'
                elif y < 0:
                    block_type = 'dirt'
                else:
                    block_type = 'grass'
                blocks[(x + offset_x * chunk_size, y, z + offset_z * chunk_size)] = block_type

    chunk_data = {}
    for pos, block_type in blocks.items():
        x, y, z = pos
        visible_faces = [
            (x, y, z - 1) not in blocks,  # front face
            (x, y, z + 1) not in blocks,  # back face
            (x, y + 1, z) not in blocks,  # top face
            (x, y - 1, z) not in blocks,  # bottom face
            (x + 1, y, z) not in blocks,  # right face
            (x - 1, y, z) not in blocks   # left face
        ]
        chunk_data[pos] = (block_type, visible_faces)

    print(f"Generated chunk at ({offset_x}, {offset_z}) with {len(chunk_data)} blocks.")
    return chunk_data

def update_chunks(chunks, current_pos, chunk_size=16, render_distance=2):
    """
    Update the chunks: add new ones around the current position and remove those that are too far.
    """
    min_x = current_pos[0] - render_distance
    max_x = current_pos[0] + render_distance
    min_z = current_pos[1] - render_distance
    max_z = current_pos[1] + render_distance

    new_chunks = [(x, z) for x in range(min_x // chunk_size, (max_x + chunk_size - 1) // chunk_size + 1)
                           for z in range(min_z // chunk_size, (max_z + chunk_size - 1) // chunk_size + 1)]

    # Add new chunks
    for pos in new_chunks:
        if pos not in chunks:
            chunks[pos] = generate_chunk(pos[0], pos[1])

    # Remove old chunks
    for pos in list(chunks.keys()):
        if pos not in new_chunks:
            del chunks[pos]
            print(f"Chunk removed at {pos}")

def check_for_opengl_errors():
    error = glGetError()
    while error != GL_NO_ERROR:
        print(f"OpenGL Error: {error}")
        error = glGetError()

def main():
    global textures

    pygame.init()
    display = (800, 600)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)
    glEnable(GL_TEXTURE_2D)
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LEQUAL)

    # Set up perspective projection and camera
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, (display[0] / display[1]), 0.1, 100.0)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    glTranslatef(0.0, 0.0, -30)

    # Set the background color to blue (sky color)
    glClearColor(0.53, 0.81, 0.92, 1.0)  # Light sky blue color

    # Load textures
    textures['dirt'] = load_texture('textures/dirt.png')
    textures['grass_top'] = load_texture('textures/grass_top.png')
    textures['grass_side'] = load_texture('textures/grass_side.png')
    textures['stone'] = load_texture('textures/stone.png')

    if None in textures.values():
        print("Error: One or more textures failed to load. Exiting.")
        pygame.quit()
        return

    # Initial chunk positions
    chunk_positions = [(0, 0), (1, 0), (0, 1), (1, 1)]  # Adjusted chunk positions for clarity
    chunks = {pos: generate_chunk(pos[0], pos[1]) for pos in chunk_positions}

    rotation_angle = 0
    camera_pos = (0, 0)  # Initial camera position (could be adjusted later)
    render_distance = 2  # Distance to render chunks

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return

        # Update chunks based on the current position
        update_chunks(chunks, camera_pos, chunk_size=16, render_distance=render_distance)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslatef(0.0, 0.0, -30)
        glRotatef(rotation_angle, 1, 1, 0)
        rotation_angle += 1  # Increment the rotation angle

        # Render all chunks
        for chunk_blocks in chunks.values():
            for position, (block_type, visible_faces) in chunk_blocks.items():
                Cube(position, block_type, visible_faces)

        check_for_opengl_errors()

        pygame.display.flip()
        pygame.time.wait(10)

if __name__ == "__main__":
    main()
