/**
 * Some basic helper functions
 */
function toggle_display(id, style) {
    var e = document.getElementById(id);

    e.style.display = (e.style.display === 'none') ? style : 'none';

}