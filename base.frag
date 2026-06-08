// ============================================================
// FRAGMENT SHADER — Mundo Voxel 3D
// Linguagem: GLSL ES 1.00 (WebGL 1.0)
// ============================================================
// Responsabilidades:
// 1. Amostrar a cor do pixel no atlas de texturas usando UV
// 2. Aplicar neblina de profundidade (depth fog)
// 3. Controlar transparência dos blocos de água
// ============================================================

precision highp float;

// --- Varyings: dados interpolados recebidos do Vertex Shader ---
varying vec2 vTexCoord;    // Coordenadas UV interpoladas
varying float vDist;       // Distância do fragmento à câmera

// --- Textura ---
uniform sampler2D uAtlas;  // Atlas de texturas (6 tiles de 16x16)

// --- Parâmetros de Neblina ---
uniform float uFogNear;   // Distância onde a neblina começa
uniform float uFogFar;    // Distância onde a neblina é total (100%)
uniform vec3  uFogColor;  // Cor da neblina (= cor do céu)

// --- Flag de Água ---
uniform float uIsWater;   // 1.0 para blocos de água, 0.0 para sólidos

void main() {
    // ==========================================================
    // FASE 4: Amostragem da Textura (Texture Sampling)
    // Busca a cor do pixel no atlas usando as coordenadas UV.
    // As UVs apontam para a tile correta no atlas baseado
    // no tipo de bloco e face (calculado no Python).
    // ==========================================================
    vec4 texColor = texture2D(uAtlas, vTexCoord);

    // ==========================================================
    // FASE 5.2: Neblina de Profundidade (Depth Fog)
    // Calcula um fator de mistura baseado na distância do
    // fragmento (pixel) até a câmera.
    //
    // Fórmula linear:
    //   fogFactor = (distância - near) / (far - near)
    //   fogFactor = clamp(fogFactor, 0.0, 1.0)
    //
    // - fogFactor = 0.0: perto da câmera, sem neblina
    // - fogFactor = 1.0: longe da câmera, neblina total
    //
    // Depois mistura a cor da textura com a cor do céu:
    //   mix(textura, céu, fator)
    // Isso esconde o limite do mapa de forma suave.
    // ==========================================================
    float fogFactor = clamp(
        (vDist - uFogNear) / (uFogFar - uFogNear),
        0.0,
        1.0
    );

    // mix(a, b, t) retorna a*(1-t) + b*t
    // Quando t=0: retorna a cor da textura (perto)
    // Quando t=1: retorna a cor do céu/neblina (longe)
    vec3 finalColor = mix(texColor.rgb, uFogColor, fogFactor);

    // Transparência: água é semi-transparente (alpha=0.65)
    // Blocos sólidos mantêm o alpha original da textura (1.0)
    float alpha = uIsWater > 0.5 ? 0.65 : texColor.a;

    // Cor final do fragmento (pixel na tela)
    gl_FragColor = vec4(finalColor, alpha);
}
