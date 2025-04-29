const BpmnModdle = require('bpmn-moddle');
const fs = require('fs');
const path = require('path');

// 创建 BpmnModdle 实例
const moddle = new BpmnModdle();

// 读取 process.txt 文件
const filePath = path.join(__dirname, 'process.txt');
fs.readFile(filePath, 'utf8', (err, data) => {
    if (err) {
        console.error('读取文件时出错:', err);
        return;
    }

    try {
        // 解析 JSON 数据
        const bpmnJson = JSON.parse(data);

        // 使用 bpmn-moddle 解析 BPMN JSON 数据
        moddle.fromJSON(bpmnJson, 'bpmn:Definitions', (parseErr, definitions) => {
            if (parseErr) {
                console.error('解析 BPMN JSON 数据时出错:', parseErr);
            } else {
                console.log('解析成功:', definitions);
            }
        });
    } catch (jsonErr) {
        console.error('解析 JSON 数据时出错:', jsonErr);
    }
});