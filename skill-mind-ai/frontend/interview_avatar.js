/**
 * AI Avatar Interviewer Module
 * Handles Three.js rendering, ReadyPlayerMe model loading, and basic animations.
 */

class AIAvatarInterviewer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) return;

        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.model = null;
        this.mixer = null;
        this.clock = new THREE.Clock();

        // Morph targets for lip-sync
        this.morphTargetVowels = ['viseme_aa', 'viseme_EE', 'viseme_ih', 'viseme_oo', 'viseme_ou'];

        this.init();
    }

    init() {
        // Scene setup
        this.scene = new THREE.Scene();
        this.scene.background = null; // Transparent background

        // Camera setup
        const aspect = this.container.clientWidth / this.container.clientHeight;
        this.camera = new THREE.PerspectiveCamera(45, aspect, 0.1, 1000);
        this.camera.position.set(0, 1.5, 2); // Positioned for portrait view

        // Renderer setup
        this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
        this.renderer.setSize(this.container.clientWidth, this.container.clientHeight);
        this.renderer.setPixelRatio(window.devicePixelRatio);
        this.renderer.outputEncoding = THREE.sRGBEncoding;
        this.container.appendChild(this.renderer.domElement);

        // Lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
        this.scene.add(ambientLight);

        const spotLight = new THREE.SpotLight(0xffffff, 0.5);
        spotLight.position.set(0, 5, 5);
        this.scene.add(spotLight);

        // Resize handler
        window.addEventListener('resize', () => this.onWindowResize());

        this.animate();
        this.loadModel();
    }

    onWindowResize() {
        const width = this.container.clientWidth;
        const height = this.container.clientHeight;
        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }

    loadModel() {
        // A very stable public ReadyPlayerMe avatar
        const modelUrl = 'https://models.readyplayer.me/64b5e65d2d057a6e11883c58.glb?morphTargets=ARKit,Oculus%20Visemes';

        const loader = new THREE.GLTFLoader();
        loader.load(modelUrl, (gltf) => {
            this.model = gltf.scene;
            this.model.position.set(0, 0, 0);
            this.scene.add(this.model);

            // Hide loader
            this.hideLoader();

            // Find morph targets for lip sync
            this.model.traverse(node => {
                if (node.isMesh && node.morphTargetDictionary) {
                    this.headMesh = node;
                }
            });

            this.mixer = new THREE.AnimationMixer(this.model);
            if (gltf.animations.length) {
                const idle = this.mixer.clipAction(gltf.animations[0]);
                idle.play();
            }

            if (this.onLoad) this.onLoad();
        }, undefined, (error) => {
            console.error('Error loading avatar:', error);
            this.hideLoader();
            if (this.onError) this.onError(error);
        });
    }

    hideLoader() {
        const loaderEl = this.container.querySelector('.avatar-loader');
        if (loaderEl) loaderEl.style.display = 'none';
    }

    // Enhanced Lip Sync
    speak(text) {
        if (!this.headMesh) return;
        this.isSpeaking = true;

        // Clear any existing speaking interval
        if (this.speakInterval) clearInterval(this.speakInterval);

        this.speakInterval = setInterval(() => {
            if (!this.isSpeaking) {
                this.resetVisemes();
                clearInterval(this.speakInterval);
                return;
            }

            // More realistic speech movement: oscillate between vowels
            this.morphTargetVowels.forEach((v, i) => {
                const idx = this.headMesh.morphTargetDictionary[v];
                if (idx !== undefined) {
                    // Random but somewhat smooth oscillation
                    const target = Math.random() > 0.5 ? Math.random() * 0.7 : 0;
                    this.headMesh.morphTargetInfluences[idx] = THREE.MathUtils.lerp(
                        this.headMesh.morphTargetInfluences[idx],
                        target,
                        0.3
                    );
                }
            });
        }, 60);
    }

    stopSpeak() {
        this.isSpeaking = false;
    }

    resetVisemes() {
        if (!this.headMesh) return;
        this.morphTargetVowels.forEach(v => {
            const idx = this.headMesh.morphTargetDictionary[v];
            if (idx !== undefined) {
                this.headMesh.morphTargetInfluences[idx] = 0;
            }
        });
    }

    // Blinking logic
    blink() {
        if (!this.headMesh) return;
        const blinkTarget = this.headMesh.morphTargetDictionary['eyeBlinkLeft'] !== undefined ? 'eyeBlink' : 'eyesClosed';
        const leftIdx = this.headMesh.morphTargetDictionary[blinkTarget + 'Left'] || this.headMesh.morphTargetDictionary['eyesClosed'];
        const rightIdx = this.headMesh.morphTargetDictionary[blinkTarget + 'Right'] || this.headMesh.morphTargetDictionary['eyesClosed'];

        if (leftIdx === undefined) return;

        // Rapid close and open
        this.headMesh.morphTargetInfluences[leftIdx] = 1;
        this.headMesh.morphTargetInfluences[rightIdx] = 1;

        setTimeout(() => {
            if (this.headMesh) {
                this.headMesh.morphTargetInfluences[leftIdx] = 0;
                this.headMesh.morphTargetInfluences[rightIdx] = 0;
            }
        }, 150);
    }

    updateIdle(delta) {
        if (!this.model) return;

        const time = Date.now() * 0.001;

        // Subtle head sway (more natural)
        this.model.rotation.y = Math.sin(time * 0.5) * 0.04 + Math.sin(time * 0.2) * 0.02;
        this.model.rotation.x = Math.cos(time * 0.4) * 0.015;

        // Eye movement (subtle looking around)
        if (this.headMesh) {
            const eyeLookLeftIdx = this.headMesh.morphTargetDictionary['eyeLookInLeft'] || this.headMesh.morphTargetDictionary['eyeLookOutRight'];
            const eyeLookRightIdx = this.headMesh.morphTargetDictionary['eyeLookInRight'] || this.headMesh.morphTargetDictionary['eyeLookOutLeft'];

            if (eyeLookLeftIdx !== undefined && eyeLookRightIdx !== undefined) {
                const lookVal = Math.sin(time * 0.3) * 0.2;
                this.headMesh.morphTargetInfluences[eyeLookLeftIdx] = Math.max(0, lookVal);
                this.headMesh.morphTargetInfluences[eyeLookRightIdx] = Math.max(0, -lookVal);
            }
        }

        // Breathing effect
        const spine = this.model.getObjectByName('Spine');
        if (spine) {
            spine.rotation.x = Math.sin(time * 1.5) * 0.02 + 0.04;
        }
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        const delta = this.clock.getDelta();
        if (this.mixer) this.mixer.update(delta);

        this.updateIdle(delta);

        // Random blinking
        if (Math.random() < 0.004) {
            this.blink();
        }

        if (this.renderer && this.scene && this.camera) {
            this.renderer.render(this.scene, this.camera);
        }
    }
}

// Export for use in script.js
window.AIAvatarInterviewer = AIAvatarInterviewer;
