function highlight(){
 var table = document.getElementById('dataTable');
 for (var i=1;i < table.rows.length;i++){
  table.rows[i].onclick= function () {
   if(!this.hilite){
    this.origColor=this.style.backgroundColor;
    this.style.backgroundColor='#dd8542';
    this.hilite = true;
   }
   else if(!this.hilite2){
    this.style.backgroundColor='#a27ff9';
    this.hilite2 = true;
   }
   else{
    this.style.backgroundColor=this.origColor;
    this.hilite = false;
    this.hilite2 = false;
   }
  }
 }
}

window.onload = highlight;