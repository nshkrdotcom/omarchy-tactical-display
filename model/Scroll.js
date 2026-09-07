// ScrollView owns a Flickable contentItem; it has no contentY property itself.
function position(current, height, contentHeight, top, itemHeight) {
    var next=current;
    if (top<current || itemHeight>height) next=top;
    else if (top+itemHeight>current+height) next=top+itemHeight-height;
    return Math.max(0,Math.min(Math.max(0,contentHeight-height),next));
}
function reveal(view, item, content) {
    if (!view.contentItem || typeof view.contentItem.contentY!=='number') return;
    var point=item.mapToItem(content,0,0);
    view.contentItem.contentY=position(view.contentItem.contentY,view.availableHeight || view.height,view.contentHeight,point.y,item.height);
}
if(typeof module!=='undefined')module.exports={position:position,reveal:reveal};
