// Dark Mode Toggle Script
// Theme is pre-applied by bootstrap script in <head> to prevent flash
// This script only handles toggle and updates storage + button state
document.addEventListener('DOMContentLoaded', function() {
    const darkModeToggle = document.getElementById('darkModeToggle');
    const body = document.body;
    
    // Toggle dark mode on button click
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', function() {
            body.classList.toggle('dark-mode');
            
            // Update localStorage and button state
            if (body.classList.contains('dark-mode')) {
                localStorage.setItem('darkMode', 'enabled');
                darkModeToggle.innerHTML = '<i class="fas fa-sun"></i>';
                darkModeToggle.setAttribute('title', 'Toggle Light Mode');
                darkModeToggle.setAttribute('aria-label', 'Toggle light mode');
            } else {
                localStorage.setItem('darkMode', 'disabled');
                darkModeToggle.innerHTML = '<i class="fas fa-moon"></i>';
                darkModeToggle.setAttribute('title', 'Toggle Dark Mode');
                darkModeToggle.setAttribute('aria-label', 'Toggle dark mode');
            }
        });
        
        // Sync button icon with current theme state
        if (body.classList.contains('dark-mode')) {
            darkModeToggle.innerHTML = '<i class="fas fa-sun"></i>';
            darkModeToggle.setAttribute('title', 'Toggle Light Mode');
            darkModeToggle.setAttribute('aria-label', 'Toggle light mode');
        }
    }
});
