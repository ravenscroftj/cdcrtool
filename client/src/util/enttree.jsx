import React from 'react';

function EntityNode(start, end, text, primary){
        this.start = parseInt(start);
        this.end = parseInt(end);
        this.text = text;
        this.primary = primary;
        this.children=[];
    

    this.insert = (newNode)=>{

        let inserted=false;

        for (let index = 0; index < this.children.length; index++) {
            const child = this.children[index];

            if(newNode.start < child.start && newNode.end < child.start) {
                this.children.splice(index,0, newNode );
                inserted = true;
                break;
            }else if(newNode.start >= child.start && newNode.end <= child.end){
                child.insert(newNode);
                inserted = true;
                break;
            }else if(newNode.start <= child.start && newNode.end >= child.end){
                newNode.insert(child);
                this.children.splice(index, 1);
                inserted=true;
            }
        } 

        if(!inserted){
            this.children.push(newNode);
        }
    };

    this.render = (fullText) => {

        let spans = [];
        let prevStart = this.start;
        let prevEnd = this.start;

        let isRoot = !fullText;

        if (!fullText){
            fullText = this.text;
        }

        for (const child of this.children) {

            if(prevEnd < child.start){
                spans.push((<span>{fullText.substring(prevEnd, child.start)}</span>))
            }

            spans.push(child.render(fullText));

            prevStart = child.start;
            prevEnd = child.end;
        }

        if(prevEnd < this.end){
            spans.push((<span>{fullText.substring(prevEnd, this.end)}</span>));
        }

        if(isRoot){
            return (<span>{spans}</span>)
        }else{
            return this.primary ? (<mark>{spans}</mark>) :(<span className="text-info">{spans}</span>);
        }

        
    }
};

function EntityTree(doctext) {
    this.rootNode = new EntityNode(0, doctext.length, doctext);
    this.render = this.rootNode.render;
    this.insert = this.rootNode.insert;
}

export {EntityNode, EntityTree};