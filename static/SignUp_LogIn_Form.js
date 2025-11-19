// --- Toggle between login and register forms ---
const container = document.querySelector('.container');
const registerBtn = document.querySelector('.register-btn');
const loginBtn = document.querySelector('.login-btn');

registerBtn.addEventListener('click', () => container.classList.add('active'));
loginBtn.addEventListener('click', () => container.classList.remove('active'));


// --- Popup helper ---
function showPopup(id, message, duration = 2500, soundType = null) {
    const popup = document.getElementById(id);
    const text = popup.querySelector('h2');
    text.textContent = message;
    popup.style.display = 'flex';

    // Play sound if specified
    if (soundType) playSound(soundType);

    setTimeout(() => {
        popup.style.opacity = '0';
        setTimeout(() => {
            popup.style.display = 'none';
            popup.style.opacity = '1';
        }, 400);
    }, duration);
}


// --- Play success/error sounds ---
function playSound(type) {
    const sound = new Audio(type === 'success' ? '/static/success.mp3' : '/static/error.mp3');
    sound.volume = 0.3;
    sound.play().catch(err => console.warn('Sound playback skipped:', err));
}


// --- Handle Flask flash() messages ---
document.addEventListener('DOMContentLoaded', () => {
    if (window.serverMessages && window.serverMessages.length > 0) {
        window.serverMessages.forEach(msg => {
            const lowerText = msg.text.toLowerCase();

            // ✅ Handle success messages
            if (msg.category === 'success') {
                showPopup('successMessage', msg.text, 2500, 'success');

                // ✅ After successful registration → switch to Login form
                if (
                    lowerText.includes('registration successful') ||
                    lowerText.includes('you can now log in')
                ) {
                    setTimeout(() => container.classList.remove('active'), 1000);
                }

                // ✅ Handle logout or session expiration
                else if (
                    lowerText.includes('logged out') ||
                    lowerText.includes('session expired')
                ) {
                    setTimeout(() => container.classList.remove('active'), 1000);
                }
            } 
            
            // ⚠️ Handle error messages
            else if (msg.category === 'error') {
                showPopup('errorMessage', msg.text, 2500, 'error');

                // ✅ If username already exists → switch to Login form
                if (
                    lowerText.includes('already exists') ||
                    lowerText.includes('username already exists')
                ) {
                    setTimeout(() => container.classList.remove('active'), 1000);
                }

                // ✅ If told to register first → switch to Register form
                else if (
                    lowerText.includes('register') ||
                    lowerText.includes('sign up')
                ) {
                    setTimeout(() => container.classList.add('active'), 1000);
                }
            }
        });
    }
});


// --- Add loading effect on form submit ---
document.addEventListener('submit', (event) => {
    const form = event.target;
    const btn = form.querySelector('button[type="submit"]');
    if (btn) {
        btn.innerHTML = '<i class="bx bx-loader-circle bx-spin"></i> Processing...';
        btn.disabled = true;
    }
});
