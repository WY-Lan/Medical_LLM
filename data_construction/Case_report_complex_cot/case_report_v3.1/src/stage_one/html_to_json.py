#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML转JSON处理器：读取PMC HTML文件并转换为JSON格式
"""

import os
import sys
import json
import yaml
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from .html_parser import HTMLParser

class HTMLToJSONConverter:
    """
    将PMC HTML文件转换为结构化JSON
    优化版本：使用配置文件和改进的日志记录
    """
    
    def __init__(self, input_dir, output_dir, max_workers=8, max_items=None, config=None):
        """
        初始化转换器
        
        参数:
            input_dir (str): 输入目录路径，包含HTML文件
            output_dir (str): 输出目录路径，存储JSON结果
            max_workers (int): 最大线程数
            max_items (int, optional): 最大处理文件数，None表示处理所有文件
            config (dict, optional): 配置字典，如果提供则覆盖其他参数
        """
        # 如果提供了配置，则从配置中读取参数
        if config:
            self.input_dir = Path(config.get('paths', {}).get('input_dir', input_dir))
            self.output_dir = Path(config.get('stage_one', {}).get('output_dir', output_dir))
            self.max_workers = config.get('general', {}).get('max_workers', max_workers)
            self.max_items = config.get('general', {}).get('max_items', max_items)
            self.log_level = config.get('general', {}).get('log_level', 'INFO')
        else:
            self.input_dir = Path(input_dir)
            self.output_dir = Path(output_dir)
            self.max_workers = max_workers
            self.max_items = max_items
            self.log_level = 'INFO'
            
        # 配置日志
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, self.log_level))
        
        # 创建解析器
        self.parser = HTMLParser()
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.logger.info(f"HTMLToJSONConverter初始化完成")
        self.logger.info(f"输入目录: {self.input_dir}")
        self.logger.info(f"输出目录: {self.output_dir}")
        self.logger.info(f"最大线程数: {self.max_workers}")
        self.logger.info(f"最大处理文件数: {self.max_items if self.max_items else '不限'}")
        
    @classmethod
    def from_config_file(cls, config_path="config/default.yaml"):
        """
        从配置文件创建转换器实例
        
        参数:
            config_path (str): 配置文件路径
            
        返回:
            HTMLToJSONConverter: 转换器实例
        """
        try:
            # 加载配置文件
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                
            # 创建实例
            return cls(
                input_dir=config.get('paths', {}).get('input_dir', 'data/raw'),
                output_dir=config.get('paths', {}).get('output_dir', 'output') + '/stage_one',
                max_workers=config.get('general', {}).get('max_workers', 8),
                max_items=config.get('general', {}).get('max_items'),
                config=config
            )
        except Exception as e:
            logging.error(f"从配置文件创建转换器时出错: {str(e)}")
            raise
        
    def convert_file(self, html_file):
        """
        转换单个HTML文件为JSON
        
        参数:
            html_file (Path): HTML文件路径
            
        返回:
            bool: 转换成功返回True，否则返回False
        """
        try:
            self.logger.info(f"处理文件: {html_file}")
            
            # 确定输出JSON文件路径
            json_filename = f"{html_file.stem}.json"
            json_file = self.output_dir / json_filename
            
            # 读取HTML文件内容
            with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
                html_content = f.read()
                
            # 解析HTML内容
            article_data = self.parser.parse_html(html_content)
            
            # 添加文件元信息
            article_data['source_file'] = str(html_file.name)
            
            # 保存为JSON文件
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(article_data, f, ensure_ascii=False, indent=2)
                
            self.logger.info(f"成功转换并保存到: {json_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"转换文件 {html_file} 时出错: {str(e)}")
            return False
            
    def process_batch(self, html_files):
        """
        并行处理一批HTML文件
        
        参数:
            html_files (list): HTML文件路径列表
            
        返回:
            tuple: (成功数, 失败数)
        """
        success_count = 0
        failure_count = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {executor.submit(self.convert_file, file): file for file in html_files}
            
            for future in as_completed(future_to_file):
                file = future_to_file[future]
                try:
                    success = future.result()
                    if success:
                        success_count += 1
                    else:
                        failure_count += 1
                except Exception as e:
                    self.logger.error(f"处理文件 {file} 时发生未处理的异常: {str(e)}")
                    failure_count += 1
                    
        return success_count, failure_count
    
    def run(self):
        """
        运行批量转换处理
        
        返回:
            tuple: (成功转换数, 失败数)
        """
        self.logger.info(f"开始处理HTML文件: {self.input_dir}")
        
        # 获取所有HTML文件
        html_files = list(self.input_dir.glob('*.html'))
        
        # 根据max_items限制处理数量
        if self.max_items is not None and len(html_files) > self.max_items:
            self.logger.info(f"限制处理文件数为 {self.max_items} (共找到 {len(html_files)} 个文件)")
            html_files = html_files[:self.max_items]
        else:
            self.logger.info(f"找到 {len(html_files)} 个HTML文件")
            
        if not html_files:
            self.logger.warning(f"未找到HTML文件")
            return 0, 0
            
        # 处理所有文件
        success_count, failure_count = self.process_batch(html_files)
        
        # 输出处理结果
        self.logger.info(f"处理完成. 成功: {success_count}, 失败: {failure_count}")
        
        return success_count, failure_count


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='将PMC HTML文件转换为JSON格式')
    parser.add_argument('--input-dir', required=True, help='输入目录路径，包含HTML文件')
    parser.add_argument('--output-dir', required=True, help='输出目录路径，存储JSON结果')
    parser.add_argument('--max-workers', type=int, default=8, help='最大线程数')
    parser.add_argument('--max-items', type=int, help='最大处理文件数，不指定则处理所有文件')
    
    return parser.parse_args()
    
    
def main():
    """主函数"""
    args = parse_args()
    
    # 创建并运行转换器
    converter = HTMLToJSONConverter(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        max_workers=args.max_workers,
        max_items=args.max_items
    )
    
    converter.run()
    
    
if __name__ == "__main__":
    main()
