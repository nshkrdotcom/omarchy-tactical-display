'use strict';
const test=require('node:test'), assert=require('node:assert/strict');
const S=require('../../model/Scroll.js');
test('focus reveal scrolls the actual Flickable, never a nonexistent ScrollView property',()=>{
    const scroll={height:200,contentHeight:1000,contentItem:{contentY:0}};
    const item={height:30,mapToItem:()=>({x:0,y:700})};
    S.reveal(scroll,item,{});
    assert.equal(scroll.contentItem.contentY,530); assert.equal(scroll.contentY,undefined);
    item.mapToItem=()=>({x:0,y:100}); S.reveal(scroll,item,{}); assert.equal(scroll.contentItem.contentY,100);
});
test('focus reveal remains stable for visible controls and clamps short and oversized content',()=>{
    assert.equal(S.position(100,200,1000,150,30),100);
    assert.equal(S.position(100,200,1000,900,30),730);
    assert.equal(S.position(100,200,1000,150,500),150);
    assert.equal(S.position(100,200,100,-10,10),0);
});
