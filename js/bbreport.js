/**
 * Some basic helper functions
 */
function toggle_display(id, imgid, changeimage = true) {
    var e = document.getElementById(id);

    e.style.display = (e.style.display === 'none') ? 'block' : 'none';
    if (changeimage) {
        var img1 = "../img/iconmonstr-arrow-down-32-32.png",
            img2 = "../img/iconmonstr-arrow-up-32-32.png";

        var imgElement = document.getElementById(imgid);
        var imgfilename = imgElement.src.split(/[\/]+/).pop();
        var imgsource = "../img/" + imgfilename;
        imgElement.src = (imgsource === img1) ? img2 : img1;
    }
}