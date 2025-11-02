document.getElementById('login-btn').addEventListener('click', function () {
    const loginContainer = document.querySelector('.login-container');
    const loginForm = document.getElementById('login-form');
    const background = loginContainer.querySelector('.background-image');

    // Add transition effect to background image
    background.style.opacity = 0;

    // After background fades out, show the login form with animation
    setTimeout(function () {
        // Hide image
        loginContainer.querySelector('.background-image').classList.add('d-none');
        loginForm.classList.remove('d-none');

        loginForm.querySelector('.form-right').classList.add('show');
    }, 1000); // Adjust the delay to match the background fade
});
