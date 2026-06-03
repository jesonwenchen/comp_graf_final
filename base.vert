// ============================================================
// VERTEX SHADER — Mundo Voxel 3D
// Linguagem: GLSL ES 1.00 (WebGL 1.0)
// ============================================================
// Responsabilidades:
// 1. Transformar posições dos vértices para clip space
// 2. Animar vértices de blocos de água com ondas senoidais
// 3. Calcular distância para efeito de neblina
// 4. Repassar coordenadas UV ao Fragment Shader
// ============================================================

precision highp float;

// --- Atributos fornecidos pelo p5.js ---
// Estes são preenchidos automaticamente pelo motor gráfico
// a partir dos dados de vertex() no Python
attribute vec3 aPosition;    // Posição 3D do vértice
attribute vec2 aTexCoord;    // Coordenadas de textura (U, V)
attribute vec3 aNormal;      // Vetor normal (necessário para p5.js)

// --- Matrizes de transformação (p5.js automático) ---
uniform mat4 uModelViewMatrix;   // Model × View: transforma para eye space
uniform mat4 uProjectionMatrix;  // Projeção perspectiva: eye → clip space

// --- Uniforms customizados (passados do Python via setUniform) ---
uniform float uTempo;     // Tempo em segundos (millis()/1000)
uniform float uIsWater;   // Flag: 1.0 = água, 0.0 = sólido

// --- Varyings: dados interpolados enviados ao Fragment Shader ---
varying vec2 vTexCoord;    // UV interpolado entre vértices
varying float vDist;       // Distância do fragmento à câmera

void main() {
    // Cópia da posição original do vértice
    vec4 pos = vec4(aPosition, 1.0);

    // ==========================================================
    // FASE 5.1: Animação de Ondas para Água
    // Se este vértice pertence a um bloco de água, desloca
    // sua posição Y usando uma função senoidal.
    // A fórmula combina tempo + posição XZ para criar
    // ondas que se propagam pela superfície da água.
    // Y_novo = Y_atual + sin(tempo * vel + X * freq + Z * freq) * amplitude
    // ==========================================================
    if (uIsWater > 0.5) {
        pos.y -= sin(uTempo * 2.0 + pos.x * 3.0 + pos.z * 3.0) * 0.06;
    }

    // Repassa coordenadas UV para o fragment shader
    vTexCoord = aTexCoord;

    // Transforma o vértice para eye space (espaço da câmera)
    vec4 eyePos = uModelViewMatrix * pos;

    // Calcula distância euclidiana do vértice à câmera
    // Usado pelo fragment shader para neblina radial
    vDist = length(eyePos.xyz);

    // Posição final em clip space (o que aparece na tela)
    gl_Position = uProjectionMatrix * eyePos;
}
