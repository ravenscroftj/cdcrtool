import React from 'react';

function EntityNode(start, end, text, primary, secondary, callback, secondaryClass){
        this.start = parseInt(start);
        this.end = parseInt(end);
        this.text = text;
        this.primary = primary;
        this.secondary=secondary;
        this.children=[];
        this.callback = callback;
        this.secondaryClass = secondaryClass? secondaryClass: "text-success";

    this.insert = (newNode)=>{

        let inserted=false;

        for (let index = 0; index < this.children.length; index++) {
            const child = this.children[index];

            if(newNode.start < child.start && newNode.end < child.start) {
                this.children.splice(index,0, newNode );
                inserted = true;
                break;
            }else if(newNode.start > child.start && newNode.end < child.end){
                child.insert(newNode);
                inserted = true;
                break;
            }else if(newNode.start < child.start && newNode.end > child.end){
                newNode.insert(child);
                this.children.splice(index, 1);
                inserted=true;
            }
        } 

        if(!inserted){
            this.children.push(newNode);
        }
    };

    this.handleClick = (evt) => {
        evt.stopPropagation();
        this.callback(`${this.text};${this.start};${this.end}`);
    };

    this.render = (fullText, startFrom) => {

        let spans = [];
        let prevStart = this.start;
        let prevEnd = startFrom? Math.max(startFrom,this.start) : this.start;

        let isRoot = !fullText;

        if (!fullText){
            fullText = this.text;
        }

        for (const child of this.children) {

            if(prevEnd < child.start){
                spans.push((<div>{fullText.substring(prevEnd, child.start)}</div>))
            }

            spans.push(child.render(fullText, prevEnd));

            prevStart = child.start;
            prevEnd = child.end;
        }

        if(prevEnd < this.end){
            spans.push((<div>{fullText.substring(prevEnd, this.end)}</div>));
        }

        if(isRoot){
            return (<div>{spans}</div>)
        }else{
            if(this.primary){
                return (<mark onClick={this.handleClick}>{spans}</mark>)
            }else if(this.secondary){
                return (<div className={this.secondaryClass} onClick={this.handleClick}>{spans}</div>)
            }

            return (<div className="text-muted" onClick={this.handleClick}>{spans}</div>);
        }

        
    }
};

function EntityTree(doctext) {
    this.rootNode = new EntityNode(0, doctext.length, doctext);
    this.render = this.rootNode.render;
    this.insert = this.rootNode.insert;
}

export {EntityNode, EntityTree};