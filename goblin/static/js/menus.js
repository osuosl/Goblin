/* Toggles the Menu if it's hidden */
(function ($) {
$(document).ready(function() {

  $("#mobile-osu-top-hat a:eq(0)").prepend('<i class="icon-calendar"></i><br />');
  $("#mobile-osu-top-hat a:eq(1)").prepend('<i class="icon-book"></i><br />');
  $("#mobile-osu-top-hat a:eq(2)").prepend('<i class="icon-map-marker"></i><br />');
  $("#mobile-osu-top-hat a:eq(3)").prepend('<i class="icon-cogs"></i><br />');
  $("#mobile-osu-top-hat a:eq(4)").prepend('<i class="icon-gift"></i><br />');
  
  $("#toggle-mobile-menu").click(function() {
    
    if ($("#mobile-menu").is(":hidden")) {
      $("#mobile-menu").show("slow");
      
    } else {
      $("#mobile-menu").slideUp();
    }
  });

});
}(jQuery));