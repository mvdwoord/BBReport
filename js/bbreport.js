/**
 * Some basic helper functions
 */
function toggle_display(id, style) {
    var e = document.getElementById(id);
    var current_style = getComputedStyle(e).display;
    e.style.display = (current_style === 'none') ? style : 'none';

}