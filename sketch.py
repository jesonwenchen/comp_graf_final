# ============================================================
# MUNDO VOXEL 3D COM SHADERS GLSL
# Projeto de Computação Gráfica — Py5Script
# ============================================================
# Este programa cria um mini-mundo voxel estilo Minecraft com:
#   - Câmera em primeira pessoa (FPS) com braço estilo Minecraft
#   - Geração procedural de terreno com Perlin noise
#   - Shaders GLSL para texturas, neblina e animação de água
#   - Física: gravidade e colisão AABB
#   - Interação: adicionar/remover blocos com mouse
#   - Crosshair (mira) no centro da tela
#
# Plataforma: Py5Script (p5.js + PyScript no browser)
# Renderer: WEBGL
# Shaders: GLSL ES 1.00 (WebGL 1.0)
# ============================================================

# Importa módulo random do Python (p5.js random() não é auto-prefixado no Py5Script)
import random as pyrandom

# =================================================================
# CONSTANTES DO MUNDO
# =================================================================
WORLD_SIZE = 48        # Largura e profundidade do mapa em blocos
MAX_HEIGHT = 12        # Altura máxima que o terreno pode atingir
SEA_LEVEL  = 4         # Nível do mar: água preenche até essa altura
BLOCK_SIZE = 1         # Tamanho de cada bloco cúbico

# =================================================================
# TIPOS DE BLOCO (IDs)
# =================================================================
AIR    = 0             # Vazio (ar) — sem bloco
DIRT   = 1             # Terra (marrom)
GRASS  = 2             # Grama (topo verde, lados marrom/verde)
WATER  = 3             # Água (azul translúcido)
WOOD   = 4             # Tronco de árvore (madeira)
LEAVES = 5             # Folhas de árvore (verde escuro)

# =================================================================
# CONSTANTES DA CÂMERA E FÍSICA
# =================================================================
MOVE_SPEED    = 0.15   # Velocidade de deslocamento por frame
SENSITIVITY   = 0.003  # Sensibilidade de rotação do mouse
GRAVITY       = 0.008  # Aceleração gravitacional por frame
JUMP_FORCE    = 0.2   # Impulso vertical ao pular
PLAYER_HEIGHT = 1.62   # Altura dos olhos do jogador acima dos pés
PLAYER_RADIUS = 0.3    # Meio-largura da caixa de colisão do jogador
REACH         = 6      # Alcance máximo para interagir com blocos



# =================================================================
# VARIÁVEIS GLOBAIS
# =================================================================
# --- Câmera (posição e orientação) ---
cam_x = 0.0            # Posição X do jogador no mundo
cam_y = 0.0            # Posição Y (altura) do jogador
cam_z = 0.0            # Posição Z do jogador no mundo
yaw   = 0.0            # Ângulo horizontal de rotação (radianos)
pitch = 0.0            # Ângulo vertical de rotação (radianos)

# --- Física ---
vel_y     = 0.0        # Velocidade vertical atual
on_ground = False      # True se o jogador está pisando em bloco
noclip    = False      # False = colisão ativa + gravidade (toggle: G)

# --- Mundo ---
# Dicionário principal: mapeia coordenadas (x,y,z) ao tipo de bloco
# Exemplo: world[(5, 3, 7)] = GRASS
world = {}

# --- Malha pré-computada (faces visíveis) ---
# Cada face é uma lista de 4 vértices: [(x,y,z,u,v), ...]
solid_faces = []       # Faces de blocos sólidos (terra, grama)
water_faces = []       # Faces de blocos de água

# --- Geometria retida (GPU) ---
# Listas de objetos p5.Geometry criados com buildGeometry()
# Cada lista contém chunks de geometria para evitar stack overflow
solid_geos = []        # Chunks de blocos sólidos (terra, grama, madeira, folhas)
water_geos = []        # Chunks de blocos de água

# --- Input ---
keys_pressed = set()   # Conjunto de teclas atualmente pressionadas

# --- Shader e Textura ---
shader_base = None     # Shader GLSL carregado (vertex + fragment)
atlas       = None     # Texture atlas (p5.Graphics 128x16)

# --- Estado do Jogo ---
game_started = False   # Controla a tela de início


# =================================================================
# FASE 4: CRIAÇÃO DO TEXTURE ATLAS (Procedural)
# =================================================================
# O atlas é uma imagem de 128x16 pixels contendo 8 slots de 16x16.
# Cada tile representa a textura de um tipo de bloco/face.
# (6 tiles usados + 2 slots vazios para manter dimensões POT)
#
# IMPORTANTE: WebGL 1.0 exige texturas com dimensões potência de 2
# (power-of-two) para renderização correta. 128x16 = POT.
#
# Layout do atlas (cada coluna = 16px):
# | Tile 0: Terra | Tile 1: Grama topo | Tile 2: Grama lado | Tile 3: Água | Tile 4: Madeira | Tile 5: Folhas | (vazio) | (vazio) |
#
# Coordenadas UV normalizadas (0 a 1):
#   Tile 0: u ∈ [0.000, 0.125]
#   Tile 1: u ∈ [0.125, 0.250]
#   Tile 2: u ∈ [0.250, 0.375]
#   Tile 3: u ∈ [0.375, 0.500]
#   Tile 4: u ∈ [0.500, 0.625]
#   Tile 5: u ∈ [0.625, 0.750]
# =================================================================
def createTextureAtlas():
    """Gera o atlas de texturas pixel a pixel usando createGraphics."""
    pg = createGraphics(128, 16)
    pg.noStroke()

    # --- Tile 0: Terra (marrom com variação de pixels) ---
    # Simula textura de terra com ruído nos canais RGB
    for px in range(16):
        for py in range(16):
            r = 139 + pyrandom.randint(-20, 20)
            g = 90  + pyrandom.randint(-15, 15)
            b = 43  + pyrandom.randint(-12, 12)
            pg.fill(r, g, b)
            pg.rect(px, py, 1, 1)

    # --- Tile 1: Grama topo (verde com variação) ---
    # Vista de cima do bloco de grama
    for px in range(16):
        for py in range(16):
            r = 55  + pyrandom.randint(-12, 12)
            g = 140 + pyrandom.randint(-20, 20)
            b = 15  + pyrandom.randint(-8, 8)
            pg.fill(r, g, b)
            pg.rect(16 + px, py, 1, 1)

    # --- Tile 2: Grama lado (faixa verde no topo + terra) ---
    # Vista lateral do bloco de grama: grama na parte superior,
    # terra na parte inferior
    for px in range(16):
        for py in range(16):
            if py < 3:
                # Faixa verde superior (grama)
                r = 55  + pyrandom.randint(-12, 12)
                g = 140 + pyrandom.randint(-20, 20)
                b = 15  + pyrandom.randint(-8, 8)
            else:
                # Parte inferior (terra)
                r = 139 + pyrandom.randint(-20, 20)
                g = 90  + pyrandom.randint(-15, 15)
                b = 43  + pyrandom.randint(-12, 12)
            pg.fill(r, g, b)
            pg.rect(32 + px, py, 1, 1)

    # --- Tile 3: Água (azul com leve variação) ---
    for px in range(16):
        for py in range(16):
            r = 25  + pyrandom.randint(-8, 8)
            g = 90  + pyrandom.randint(-15, 15)
            b = 200 + pyrandom.randint(-15, 15)
            pg.fill(r, g, b)
            pg.rect(48 + px, py, 1, 1)

    # --- Tile 4: Madeira / Tronco (bark pattern com anéis e veios) ---
    for px in range(16):
        for py in range(16):
            # Padrão de casca de árvore: listras verticais escuras
            is_bark_line = (px % 3 == 0) or (px % 5 == 0 and py % 4 < 2)
            if is_bark_line:
                # Linhas escuras da casca
                r = 60  + pyrandom.randint(-10, 10)
                g = 35  + pyrandom.randint(-8, 8)
                b = 15  + pyrandom.randint(-5, 5)
            else:
                # Corpo da madeira (marrom médio)
                r = 120 + pyrandom.randint(-15, 15)
                g = 75  + pyrandom.randint(-10, 10)
                b = 30  + pyrandom.randint(-8, 8)
            pg.fill(r, g, b)
            pg.rect(64 + px, py, 1, 1)

    # --- Tile 5: Folhas (verde vibrante e brilhante) ---
    for px in range(16):
        for py in range(16):
            # Variação densa simulando folhas individuais
            bright = pyrandom.random() > 0.3
            if bright:
                # Folhas claras (maioria)
                r = 20  + pyrandom.randint(-10, 10)
                g = 160 + pyrandom.randint(-30, 30)
                b = 30  + pyrandom.randint(-15, 15)
            else:
                # Sombras entre folhas (escuras)
                r = 10  + pyrandom.randint(-5, 5)
                g = 90  + pyrandom.randint(-20, 20)
                b = 15  + pyrandom.randint(-8, 8)
            pg.fill(r, g, b)
            pg.rect(80 + px, py, 1, 1)

    return pg


# =================================================================
# FASE 3: GERAÇÃO PROCEDURAL DE TERRENO
# =================================================================
# Usa Perlin noise para criar elevações naturais (montanhas/vales).
# O ruído é amostrado nos eixos X e Z para determinar a altura
# de cada coluna de blocos.
# =================================================================
def generateTerrain():
    """Preenche o dicionário world com terreno gerado por Perlin noise."""
    global world
    world = {}

    # Seed aleatório garante terreno diferente a cada execução
    noiseSeed(pyrandom.randint(0, 10000))

    for x in range(WORLD_SIZE):
        for z in range(WORLD_SIZE):
            # noise() retorna valor entre 0 e 1
            # Multiplicador 0.08 controla a "escala" das montanhas:
            #   - Valores menores = montanhas mais largas e suaves
            #   - Valores maiores = terreno mais acidentado
            n = noise(x * 0.08, z * 0.08)
            h = int(n * MAX_HEIGHT) + 1

            # Preenche a coluna de terra desde Y=0 até h-1
            for y in range(h):
                world[(x, y, z)] = DIRT

            # Camada de grama no topo da coluna de terra
            world[(x, h, z)] = GRASS

            # --- Fase 3.2: Nível do Mar ---
            # Se o topo do terreno está abaixo de SEA_LEVEL,
            # preenche o espaço vazio com blocos de água
            if h < SEA_LEVEL:
                for y in range(h + 1, SEA_LEVEL + 1):
                    world[(x, y, z)] = WATER

    # --- Fase 3.3: Geração de Árvores ---
    # Planta árvores aleatoriamente em blocos de grama acima do nível do mar.
    # Cada árvore tem um tronco de 4-6 blocos e uma copa esférica de folhas.
    generateTrees()


# =================================================================
# FASE 3.3: GERAÇÃO PROCEDURAL DE ÁRVORES
# =================================================================
# Após gerar o terreno, percorre todas as colunas procurando
# blocos de grama acima do nível do mar. Plantas árvores com
# probabilidade de ~3%, com espaçamento mínimo de 4 blocos.
# Cada árvore tem tronco de WOOD e copa esférica de LEAVES.
# =================================================================
def generateTrees():
    """Planta árvores procedurais no terreno gerado."""
    global world

    # Coleta posições de grama válidas para árvores
    # (acima do nível do mar e longe das bordas do mapa)
    tree_positions = []
    margin = 3  # Margem das bordas para a copa não sair do mapa

    for x in range(margin, WORLD_SIZE - margin):
        for z in range(margin, WORLD_SIZE - margin):
            # Encontra o bloco de grama mais alto nesta coluna
            for y in range(MAX_HEIGHT + 1, -1, -1):
                if world.get((x, y, z)) == GRASS:
                    # Só planta acima do nível do mar
                    if y >= SEA_LEVEL:
                        # ~3% de chance de gerar árvore
                        if pyrandom.random() < 0.03:
                            # Verifica espaçamento mínimo com outras árvores
                            too_close = False
                            for tx, ty, tz in tree_positions:
                                dist_sq = (x - tx) ** 2 + (z - tz) ** 2
                                if dist_sq < 16:  # 4^2 = distância mínima
                                    too_close = True
                                    break
                            if not too_close:
                                tree_positions.append((x, y, z))
                    break  # Encontrou o topo, vai pra próxima coluna

    # Gera cada árvore na posição escolhida
    for tx, ty, tz in tree_positions:
        # Altura do tronco: 4 a 6 blocos
        trunk_height = pyrandom.randint(4, 6)

        # --- Tronco ---
        for dy in range(1, trunk_height + 1):
            world[(tx, ty + dy, tz)] = WOOD

        # --- Copa de folhas (esfera) ---
        leaf_radius = pyrandom.randint(2, 3)
        leaf_center_y = ty + trunk_height  # Centro da copa no topo do tronco

        for lx in range(-leaf_radius, leaf_radius + 1):
            for ly in range(-leaf_radius, leaf_radius + 1):
                for lz in range(-leaf_radius, leaf_radius + 1):
                    # Distância do centro da copa (esfera)
                    dist_sq = lx * lx + ly * ly + lz * lz
                    if dist_sq <= leaf_radius * leaf_radius + 1:
                        bx = tx + lx
                        by = leaf_center_y + ly
                        bz = tz + lz
                        # Só coloca folha se a posição está dentro do mundo
                        # e não sobrescreve blocos sólidos existentes
                        if 0 <= bx < WORLD_SIZE and 0 <= bz < WORLD_SIZE and by >= 0:
                            existing = world.get((bx, by, bz), AIR)
                            if existing == AIR:
                                world[(bx, by, bz)] = LEAVES


# =================================================================
# FASE 2: CULLING DE FACES E CONSTRUÇÃO DA MALHA
# =================================================================
# Para cada bloco no mundo, verificamos seus 6 vizinhos.
# Uma face só é desenhada se o vizinho naquela direção for:
#   - Ar (AIR = 0): face fica exposta ao vazio
#   - Água (WATER): face visível através da água translúcida
#     (apenas se o bloco atual NÃO é água)
# =================================================================

# Direções das 6 faces de um cubo: (nome, dx, dy, dz)
FACE_DIRS = [
    ("top",    0,  1,  0),   # Face superior (+Y)
    ("bottom", 0, -1,  0),   # Face inferior (-Y)
    ("front",  0,  0,  1),   # Face frontal  (+Z)
    ("back",   0,  0, -1),   # Face traseira (-Z)
    ("right",  1,  0,  0),   # Face direita  (+X)
    ("left",  -1,  0,  0),   # Face esquerda (-X)
]

# Vértices de cada face de um cubo unitário na origem (0,0,0)
# Ordem counter-clockwise (CCW) vista de fora do cubo
# Isso garante que as normais apontem para fora
FACE_VERTS = {
    "top":    [(0,1,0), (0,1,1), (1,1,1), (1,1,0)],
    "bottom": [(0,0,0), (1,0,0), (1,0,1), (0,0,1)],
    "front":  [(0,0,1), (1,0,1), (1,1,1), (0,1,1)],
    "back":   [(1,0,0), (0,0,0), (0,1,0), (1,1,0)],
    "right":  [(1,0,1), (1,0,0), (1,1,0), (1,1,1)],
    "left":   [(0,0,0), (0,0,1), (0,1,1), (0,1,0)],
}

# Cantos UV para mapear cada vértice de um quad ao tile do atlas
# (u_local, v_local) — multiplicados pelo tamanho do tile (1/8 = 0.125)
# Atlas é 128x16 (POT) com 8 slots de 16px, 6 usados
TILE_UV = 1.0 / 8.0    # Cada tile ocupa 1/8 do atlas (0.125)
UV_CORNERS = [(0, 1), (1, 1), (1, 0), (0, 0)]


def getTileIndex(block_type, face_name):
    """Retorna o índice do tile no atlas (0-5) baseado no tipo e face."""
    if block_type == DIRT:
        return 0                    # Tile 0: textura de terra
    elif block_type == GRASS:
        if face_name == "top":
            return 1                # Tile 1: grama vista de cima
        elif face_name == "bottom":
            return 0                # Tile 0: fundo da grama = terra
        else:
            return 2                # Tile 2: lateral da grama
    elif block_type == WATER:
        return 3                    # Tile 3: textura de água
    elif block_type == WOOD:
        return 4                    # Tile 4: textura de madeira/tronco
    elif block_type == LEAVES:
        return 5                    # Tile 5: textura de folhas
    return 0


def buildMesh():
    """Percorre todos os blocos e constrói listas de faces visíveis."""
    global solid_faces, water_faces
    solid_faces = []
    water_faces = []

    for (bx, by, bz), btype in world.items():
        # Para cada uma das 6 faces do bloco...
        for face_name, dx, dy, dz in FACE_DIRS:
            # Posição do bloco vizinho nesta direção
            nx, ny, nz = bx + dx, by + dy, bz + dz
            neighbor = world.get((nx, ny, nz), AIR)

            # --- Regra de Visibilidade ---
            # Desenha a face se:
            #   1) O vizinho é ar (face exposta ao vazio), OU
            #   2) O vizinho é água E o bloco atual NÃO é água
            #      (permite ver blocos sólidos através da água), OU
            #   3) O vizinho é folha E o bloco atual NÃO é folha
            #      (permite ver blocos sólidos através das folhas)
            should_draw = False
            if neighbor == AIR:
                should_draw = True
            elif neighbor == WATER and btype != WATER:
                should_draw = True
            elif neighbor == LEAVES and btype != LEAVES:
                should_draw = True

            if should_draw:
                # Calcula o tile no atlas e as coordenadas UV
                tile = getTileIndex(btype, face_name)
                u_base = tile * TILE_UV    # Início do tile no atlas

                # Constrói os 4 vértices da face com posição + UV
                verts = FACE_VERTS[face_name]
                face_data = []
                for i in range(4):
                    vx, vy, vz = verts[i]
                    cu, cv = UV_CORNERS[i]
                    # UV final: offset do tile + posição dentro do tile
                    u = u_base + cu * TILE_UV
                    v = float(cv)
                    face_data.append((bx + vx, by + vy, bz + vz, u, v))

                # Separa faces sólidas e de água para renderização
                if btype == WATER:
                    water_faces.append(face_data)
                else:
                    solid_faces.append(face_data)


# =================================================================
# CONSTRUÇÃO DE GEOMETRIA RETIDA (Retained Mode)
# =================================================================
# Em vez de enviar milhares de vértices à GPU a cada frame,
# usamos buildGeometry() para pré-compilar a malha.
# O resultado são listas de objetos p5.Geometry renderizados com model().
#
# Para mundos grandes (128x128+), as faces são divididas em chunks
# de MAX_FACES_PER_CHUNK para evitar stack overflow no p5.js.
#
# Vantagem: renderização rápida (poucos draw calls vs milhares)
# Quando chamar: no setup() e sempre que blocos mudarem
# =================================================================
MAX_FACES_PER_CHUNK = 5000  # Máximo de faces (quads) por chunk de geometria


def _buildChunkedGeo(face_list):
    """Divide uma lista de faces em chunks e constrói geometria retida para cada um."""
    geos = []
    total = len(face_list)
    for start in range(0, total, MAX_FACES_PER_CHUNK):
        chunk = face_list[start:start + MAX_FACES_PER_CHUNK]
        # Cria closure capturando o chunk específico
        def make_geo(faces=chunk):
            texture(atlas)
            textureMode(NORMAL)
            noStroke()
            beginShape(QUADS)
            for face in faces:
                for vx, vy, vz, u, v in face:
                    vertex(vx, -vy, vz, u, v)
            endShape()
        geos.append(buildGeometry(make_geo))
    return geos


def rebuildGeometry():
    """Reconstrói os objetos de geometria retida após mudanças."""
    global solid_geos, water_geos

    # Primeiro, reconstrói as listas de faces visíveis
    buildMesh()

    # --- Geometria dos blocos sólidos (em chunks) ---
    solid_geos = _buildChunkedGeo(solid_faces) if len(solid_faces) > 0 else []

    # --- Geometria dos blocos de água (em chunks) ---
    water_geos = _buildChunkedGeo(water_faces) if len(water_faces) > 0 else []


# =================================================================
# FASE 6: RAYCASTING (detecção de bloco na mira)
# =================================================================
# Lança um raio invisível na direção que a câmera aponta,
# avançando em pequenos passos, até encontrar um bloco sólido.
# Retorna: (posição_do_bloco, posição_anterior_ao_bloco)
# =================================================================
def raycast():
    """Lança raio da câmera e retorna (bloco_atingido, posição_anterior)."""
    # Direção normalizada da câmera (vetor forward)
    fx = cos(pitch) * sin(yaw)
    fy = sin(pitch)
    fz = cos(pitch) * cos(yaw)

    prev_pos = None
    step = 0.15   # Tamanho de cada passo do raio

    for i in range(int(REACH / step)):
        t = i * step
        # Posição atual do raio
        rx = cam_x + fx * t
        ry = cam_y + fy * t
        rz = cam_z + fz * t

        # Converte posição contínua para coordenada de bloco (inteiro)
        bx = int(floor(rx))
        by = int(floor(ry))
        bz = int(floor(rz))
        block_pos = (bx, by, bz)

        # Verifica se há bloco sólido nesta posição
        if block_pos in world and world[block_pos] != WATER:
            return (block_pos, prev_pos)

        prev_pos = block_pos

    # Nenhum bloco encontrado no alcance
    return (None, None)


# =================================================================
# FASE 6: FÍSICA — Gravidade e Colisão AABB
# =================================================================
# O jogador tem uma caixa de colisão (AABB) invisível.
# Antes de mover, verificamos se a posição futura colide
# com algum bloco sólido no dicionário do mundo.
# =================================================================
def checkCollisionAt(x, y, z):
    """Verifica se a posição (x,y,z) colide com bloco sólido."""
    # Testa vários pontos da caixa de colisão do jogador
    # (cantos inferior e superior nos eixos X e Z)
    for dx_off in [-PLAYER_RADIUS, PLAYER_RADIUS]:
        for dz_off in [-PLAYER_RADIUS, PLAYER_RADIUS]:
            # Testa na altura dos pés e do corpo
            for dy_off in [-PLAYER_HEIGHT, -PLAYER_HEIGHT * 0.5, -0.1]:
                bx = int(floor(x + dx_off))
                by = int(floor(y + dy_off))
                bz = int(floor(z + dz_off))
                block = world.get((bx, by, bz), AIR)
                # Colide apenas com blocos sólidos (não com ar ou água)
                if block != AIR and block != WATER and block != LEAVES:
                    return True
    return False


def updatePhysics():
    """Aplica gravidade e resolve colisões verticais."""
    global cam_y, vel_y, on_ground

    # Sem física no modo noclip
    if noclip:
        return

    # Aceleração gravitacional (puxa para baixo)
    vel_y -= GRAVITY

    # Posição vertical futura
    new_y = cam_y + vel_y

    # --- Colisão com o chão (caindo) ---
    if vel_y < 0:
        # Coordenada dos pés do jogador
        feet_y = new_y - PLAYER_HEIGHT
        bx = int(floor(cam_x))
        by = int(floor(feet_y))
        bz = int(floor(cam_z))
        block = world.get((bx, by, bz), AIR)

        if block != AIR and block != WATER:
            # Jogador aterrissou: posiciona em cima do bloco
            cam_y = by + 1 + PLAYER_HEIGHT
            vel_y = 0
            on_ground = True
            return

    # --- Colisão com o teto (subindo) ---
    if vel_y > 0:
        head_y = new_y + 0.1
        bx = int(floor(cam_x))
        by = int(floor(head_y))
        bz = int(floor(cam_z))
        block = world.get((bx, by, bz), AIR)

        if block != AIR and block != WATER:
            vel_y = 0
            return

    cam_y = new_y
    on_ground = False


# =================================================================
# FASE 6: CROSSHAIR (Mira no centro da tela)
# =================================================================
def drawCrosshair():
    """Desenha a mira (+) como overlay 2D sobre a cena 3D."""
    push()
    # Desativa o shader customizado para usar o padrão do p5.js
    resetShader()
    # Reseta câmera e projeção para coordenadas de tela
    camera()
    ortho()
    # Configuração visual da mira
    noFill()
    stroke(255)           # Branco
    strokeWeight(2)
    # Em WEBGL, a origem (0,0) é o centro do canvas
    line(-10, 0, 10, 0)   # Linha horizontal da mira
    line(0, -10, 0, 10)   # Linha vertical da mira
    pop()


# =================================================================
# BRAÇO DO JOGADOR (HUD — primeira pessoa, estilo Minecraft)
# =================================================================
# Desenha um braço 3D no canto inferior direito da tela como
# overlay, independente da câmera do mundo. Usa projeção
# ortográfica separada para ficar fixo na tela.
# Inclui micro-animação de balanço (idle bobbing).
# =================================================================
def drawArm():
    """Desenha o braço do jogador no HUD (canto inferior direito).
    
    Usa camera() + ortho() (mesma técnica do crosshair) para
    desenhar o braço como overlay. Em ortho, objetos em Z≈0
    ficam na frente de toda geometria do mundo (depth ≈ 0).
    """
    push()
    resetShader()
    # Mesma técnica do crosshair: reseta câmera e usa ortho
    # Em ortho, (0,0) = centro da tela
    # width/2 = borda direita, height/2 = borda inferior
    camera()
    ortho()
    noStroke()

    # --- Posição: canto inferior direito da tela ---
    translate(width * 0.28, height * 0.22, 0)

    # --- Micro-animação idle (respiração) ---
    bob = sin(millis() / 400.0) * 2.5
    translate(0, bob, 0)

    # --- Orientação: aponta do canto inferior direito → centro ---
    rotateZ(-0.65)      # Gira diagonalmente para cima-esquerda
    rotateY(0.3)        # Leve rotação 3D para dar profundidade
    rotateX(-0.15)      # Leve inclinação para frente

    # --- Braço / antebraço (cor de pele) ---
    push()
    fill(230, 190, 150)
    box(35, 150, 28)
    pop()

    # --- Mão (ponta do braço, mais escura) ---
    push()
    translate(0, -90, 0)
    fill(215, 175, 135)
    box(33, 30, 26)
    pop()

    pop()


# =================================================================
# FUNÇÕES DE CICLO DE VIDA DO p5.js
# =================================================================

def preload():
    """Carrega recursos assíncronos antes do setup().
    
    O p5.js garante que todos os recursos carregados em preload()
    estarão disponíveis quando setup() for chamado.
    """
    global shader_base
    # Carrega os arquivos de shader GLSL do projeto
    shader_base = loadShader("base.vert", "base.frag")


def setup():
    """Inicialização única do programa.
    
    Executada uma vez após preload(). Configura canvas, gera
    o mundo e prepara todos os recursos para renderização.
    """
    global atlas, cam_x, cam_y, cam_z

    # Cria canvas 3D usando WebGL
    createCanvas(800, 600, WEBGL)

    # Gera o atlas de texturas proceduralmente (4 tiles)
    atlas = createTextureAtlas()

    # Gera o terreno com Perlin noise
    generateTerrain()

    # Constrói as faces visíveis e a geometria retida na GPU
    rebuildGeometry()

    # Posição inicial da câmera: centro do mapa, acima do terreno
    cam_x = WORLD_SIZE / 2.0
    cam_y = MAX_HEIGHT + 5.0
    cam_z = WORLD_SIZE / 2.0

    # Configura renderização
    textureMode(NORMAL)     # UVs normalizados (0 a 1)
    noStroke()              # Sem contornos nos blocos


def draw():
    """Loop principal de renderização.
    
    Chamada ~60 vezes por segundo. Atualiza input, física,
    câmera e renderiza todo o mundo com shaders.
    """
    global yaw, pitch, cam_x, cam_y, cam_z, vel_y, on_ground

    # ==========================================================
    # TELA DE INÍCIO — exibida antes do primeiro clique
    # ==========================================================
    if not game_started:
        background(30, 30, 50)
        push()
        camera()
        ortho()
        fill(255)
        noStroke()
        textAlign(CENTER, CENTER)
        textSize(28)
        text("MUNDO VOXEL 3D", 0, -60)
        textSize(14)
        fill(200)
        text("Clique para iniciar", 0, -20)
        text("WASD = Mover  |  Mouse = Olhar", 0, 10)
        text("Esq = Remover bloco  |  Dir = Adicionar", 0, 35)
        text("SPACE = Pular  |  G = Noclip", 0, 60)
        pop()
        return

    # ==========================================================
    # BACKGROUND — cor do céu (mesma cor da neblina no shader)
    # ==========================================================
    background(135, 206, 235)

    # Configura projeção perspectiva a cada frame
    # (necessário porque o crosshair usa ortho())
    perspective(PI / 3.0, width / height, 0.1, 200.0)

    # ==========================================================
    # FASE 1.2: CÂMERA FPS — Rotação com Mouse
    # ==========================================================
    # movedX/movedY: delta do mouse desde o último frame
    # Com pointer lock ativo, dão movimento relativo ilimitado
    yaw   -= movedX * SENSITIVITY
    pitch  = constrain(pitch - movedY * SENSITIVITY,
                       -HALF_PI + 0.1, HALF_PI - 0.1)

    # Vetor "forward" — direção que a câmera aponta
    # Calculado com trigonometria esférica a partir de yaw e pitch
    fx = cos(pitch) * sin(yaw)    # Componente X
    fy = sin(pitch)                # Componente Y (cima/baixo)
    fz = cos(pitch) * cos(yaw)    # Componente Z

    # ==========================================================
    # FASE 1.3: MOVIMENTO WASD
    # ==========================================================
    # Vetores de direção projetados no plano horizontal (XZ)
    # "Forward" sem componente vertical — para andar no chão
    fwd_x   =  sin(yaw)
    fwd_z   =  cos(yaw)
    # "Right" = perpendicular a forward no plano XZ
    right_x = -cos(yaw)
    right_z =  sin(yaw)

    # Acumula deslocamento baseado nas teclas pressionadas
    move_x = 0.0
    move_z = 0.0

    if 'w' in keys_pressed:
        move_x += fwd_x * MOVE_SPEED
        move_z += fwd_z * MOVE_SPEED
    if 's' in keys_pressed:
        move_x -= fwd_x * MOVE_SPEED
        move_z -= fwd_z * MOVE_SPEED
    if 'a' in keys_pressed:
        move_x -= right_x * MOVE_SPEED
        move_z -= right_z * MOVE_SPEED
    if 'd' in keys_pressed:
        move_x += right_x * MOVE_SPEED
        move_z += right_z * MOVE_SPEED

    # ==========================================================
    # Aplicação do Movimento (com ou sem colisão)
    # ==========================================================
    if noclip:
        # Modo noclip: voo livre, sem gravidade nem colisão
        if ' ' in keys_pressed:
            cam_y += MOVE_SPEED      # Subir (Space)
        if 'shift' in keys_pressed:
            cam_y -= MOVE_SPEED      # Descer (Shift)
        cam_x += move_x
        cam_z += move_z
    else:
        # Pulo: só funciona quando está no chão
        if ' ' in keys_pressed and on_ground:
            vel_y = JUMP_FORCE
            on_ground = False

        # Movimento horizontal com colisão separada por eixo
        # Testa X independente de Z para permitir "deslizar" em paredes
        if not checkCollisionAt(cam_x + move_x, cam_y, cam_z):
            cam_x += move_x
        if not checkCollisionAt(cam_x, cam_y, cam_z + move_z):
            cam_z += move_z

        # Atualiza física vertical (gravidade + colisão)
        updatePhysics()

    # ==========================================================
    # CÂMERA PRIMEIRA PESSOA (FPS)
    # ==========================================================
    # A câmera está na posição dos olhos do jogador.
    # Olha na direção definida por yaw (horizontal) e pitch
    # (vertical), usando o vetor forward (fx, fy, fz).
    # Y negado para compensar o Y-flip do p5.js WEBGL.
    # ==========================================================
    camera(
        cam_x,          -cam_y,          cam_z,          # olho do jogador
        cam_x + fx,     -(cam_y + fy),   cam_z + fz,     # ponto-alvo
        0,              1,               0               # vetor up
    )

    # ==========================================================
    # FASE 4-5: RENDERIZAÇÃO COM SHADER CUSTOMIZADO
    # ==========================================================
    # Ativa o shader (substitui o pipeline padrão do p5.js)
    shader(shader_base)

    # Passa uniforms para o shader via setUniform()
    shader_base.setUniform("uTempo", millis() / 1000.0)
    shader_base.setUniform("uFogNear", 40.0)
    shader_base.setUniform("uFogFar", 110.0)
    # Cor da neblina normalizada (0-1) — mesma cor do background
    shader_base.setUniform("uFogColor", [0.529, 0.808, 0.922])
    # Passa o atlas de textura para o shader como sampler2D
    shader_base.setUniform("uAtlas", atlas)

    # Configuração de textura e renderização
    texture(atlas)
    textureMode(NORMAL)
    noStroke()

    # --- Blocos Sólidos (opacos) ---
    shader_base.setUniform("uIsWater", 0.0)
    for geo in solid_geos:
        model(geo)

    # --- Blocos de Água (translúcidos, animados no shader) ---
    shader_base.setUniform("uIsWater", 1.0)
    for geo in water_geos:
        model(geo)

    # ==========================================================
    # BRAÇO DO JOGADOR (HUD primeira pessoa)
    # ==========================================================
    drawArm()

    # ==========================================================
    # FASE 6: CROSSHAIR (overlay 2D)
    # ==========================================================
    drawCrosshair()


# =================================================================
# HANDLERS DE INPUT (Teclado e Mouse)
# =================================================================

def keyPressed():
    """Registra tecla pressionada e processa ações imediatas."""
    global noclip

    # Shift precisa de tratamento especial via keyCode
    if keyCode == 16:
        keys_pressed.add('shift')
        return

    # Converte tecla para minúsculo para comparação uniforme
    k = str(key).lower()
    keys_pressed.add(k)

    # Toggle noclip com a tecla G
    if k == 'g':
        noclip = not noclip
        # Reseta velocidade vertical ao entrar em modo noclip
        if noclip:
            global vel_y
            vel_y = 0.0


def keyReleased():
    """Remove tecla do conjunto de pressionadas ao soltar."""
    if keyCode == 16:
        keys_pressed.discard('shift')
        return

    k = str(key).lower()
    keys_pressed.discard(k)


def mousePressed():
    """Trata cliques do mouse: captura ponteiro e interage com blocos."""
    global game_started

    # Primeiro clique: inicia o jogo e captura o ponteiro
    if not game_started:
        game_started = True
        requestPointerLock()
        return

    # Re-captura o ponteiro (caso o usuário tenha saído com ESC)
    requestPointerLock()

    # ==========================================================
    # FASE 6.3: INTERAÇÃO COM BLOCOS
    # ==========================================================
    if mouseButton == LEFT:
        # Botão esquerdo: remove o bloco que está na mira
        hit_block, prev_pos = raycast()
        if hit_block is not None and hit_block in world:
            del world[hit_block]
            rebuildGeometry()     # Reconstrói malha após remoção

    elif mouseButton == RIGHT:
        # Botão direito: adiciona bloco de terra na face anterior
        hit_block, prev_pos = raycast()
        if hit_block is not None and prev_pos is not None:
            if prev_pos not in world:
                world[prev_pos] = DIRT
                rebuildGeometry()  # Reconstrói malha após adição