document.addEventListener('DOMContentLoaded', () => {
    // Background Particle Effect
    const canvas = document.createElement('canvas');
    canvas.id = 'bg-canvas';
    document.body.prepend(canvas);
    
    const ctx = canvas.getContext('2d');
    let width, height;
    
    function resize() {
        width = canvas.width = window.innerWidth;
        height = canvas.height = window.innerHeight;
    }
    
    window.addEventListener('resize', resize);
    resize();
    
    const particles = [];
    const particleCount = 50;
    
    for (let i = 0; i < particleCount; i++) {
        particles.push({
            x: Math.random() * width,
            y: Math.random() * height,
            radius: Math.random() * 2 + 1,
            vx: (Math.random() - 0.5) * 0.5,
            vy: (Math.random() - 0.5) * 0.5,
            alpha: Math.random() * 0.5 + 0.1
        });
    }
    
    function draw() {
        ctx.clearRect(0, 0, width, height);
        
        particles.forEach(p => {
            p.x += p.vx;
            p.y += p.vy;
            
            if (p.x < 0 || p.x > width) p.vx *= -1;
            if (p.y < 0 || p.y > height) p.vy *= -1;
            
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(255, 255, 255, ${p.alpha})`;
            ctx.fill();
        });
        
        requestAnimationFrame(draw);
    }
    
    draw();

    // File Drop Zone Interaction
    const dropZone = document.querySelector('.file-drop-zone');
    const fileInput = document.querySelector('input[type="file"]');
    const btnText = document.querySelector('.file-btn-text');

    if (dropZone && fileInput) {
        dropZone.addEventListener('click', (e) => {
            // Prevent duplicate clicks if the user clicked a specific button
            if (e.target.tagName !== 'BUTTON' && e.target.tagName !== 'INPUT') {
                fileInput.click();
            }
        });
        
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.style.borderColor = '#ffffff';
            dropZone.style.background = 'rgba(255, 255, 255, 0.1)';
        });
        
        dropZone.addEventListener('dragleave', () => {
            dropZone.style.borderColor = 'rgba(255,255,255,0.2)';
            dropZone.style.background = 'rgba(0,0,0,0.2)';
        });
        
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.style.borderColor = 'rgba(255,255,255,0.2)';
            dropZone.style.background = 'rgba(0,0,0,0.2)';
            
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                if (e.dataTransfer.files.length > 1) {
                    btnText.innerHTML = `Selected: <strong>${e.dataTransfer.files.length} items</strong> for packaging`;
                } else {
                    btnText.innerHTML = `Selected: <strong>${e.dataTransfer.files[0].name}</strong>`;
                }
            }
        });

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length) {
                if (fileInput.files.length > 1) {
                    btnText.innerHTML = `Selected: <strong>${fileInput.files.length} items</strong> for packaging`;
                } else {
                    btnText.innerHTML = `Selected: <strong>${fileInput.files[0].name}</strong>`;
                }
            }
        });
    }

    // Interactive Tilt on Glass Containers
    const glassContainers = document.querySelectorAll('.glass-container');
    
    glassContainers.forEach(container => {
        container.addEventListener('mousemove', (e) => {
            const rect = container.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const xPct = x / rect.width - 0.5;
            const yPct = y / rect.height - 0.5;
            
            container.style.transform = `perspective(1000px) rotateY(${xPct * 5}deg) rotateX(${-yPct * 5}deg) translateY(-5px)`;
        });
        
        container.addEventListener('mouseleave', () => {
            container.style.transform = 'perspective(1000px) rotateY(0) rotateX(0) translateY(0)';
        });
    });
});
