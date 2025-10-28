#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML解析器：负责解析PMC案例报告HTML文件，专注提取h2标题和相关内容
"""

import re
import logging
from bs4 import BeautifulSoup

class HTMLParser:
    """
    解析PMC HTML文件并提取结构化内容
    专注提取h2标题和相关内容，特别是class="pmc_sec_title"的标题
    """
    
    def __init__(self):
        """初始化解析器"""
        self.logger = logging.getLogger(__name__)
    
    def parse_html(self, html_content):
        """
        解析HTML内容并提取关键元素
        
        参数:
            html_content (str): HTML文件内容
            
        返回:
            dict: 包含解析结果的字典
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取文章标题
            title_elem = soup.find('title')
            if not title_elem:
                title_elem = soup.find('h1')
            title = title_elem.text.strip() if title_elem else "Unknown Title"
            
            # 提取文章元数据
            metadata = self._extract_metadata(soup)
            
            # 提取文章作者
            authors = self._extract_authors(soup)
            
            # 提取文章内容段落 - 专注于h2标题
            sections = self._extract_h2_sections(soup)
            
            # 构建结构化数据
            article_data = {
                "title": title,
                "metadata": metadata,
                "authors": authors,
                "sections": sections
            }
            
            return article_data
            
        except Exception as e:
            self.logger.error(f"解析HTML时出错: {str(e)}")
            raise
    
    def _extract_metadata(self, soup):
        """提取文章元数据"""
        metadata = {}
        
        # 尝试多种方式提取PMC ID
        pmc_id_elem = soup.find('article-id', attrs={'pub-id-type': 'pmc'})
        if pmc_id_elem:
            metadata['pmc_id'] = pmc_id_elem.text.strip()
        else:
            # 尝试从URL或其他位置提取PMC ID
            pmc_meta = soup.find('meta', attrs={'name': 'citation_pmid'})
            if pmc_meta and pmc_meta.get('content'):
                metadata['pmc_id'] = pmc_meta.get('content').strip()
        
        # 提取DOI
        doi_elem = soup.find('article-id', attrs={'pub-id-type': 'doi'})
        if not doi_elem:
            doi_meta = soup.find('meta', attrs={'name': 'citation_doi'})
            if doi_meta and doi_meta.get('content'):
                metadata['doi'] = doi_meta.get('content').strip()
        else:
            metadata['doi'] = doi_elem.text.strip()
        
        # 提取期刊信息
        journal_elem = soup.find('journal-title')
        if journal_elem:
            metadata['journal'] = journal_elem.text.strip()
        else:
            journal_meta = soup.find('meta', attrs={'name': 'citation_journal_title'})
            if journal_meta and journal_meta.get('content'):
                metadata['journal'] = journal_meta.get('content').strip()
        
        # 尝试提取出版日期
        pub_date = self._extract_publication_date(soup)
        if pub_date:
            metadata['publication_date'] = pub_date
        
        return metadata
    
    def _extract_publication_date(self, soup):
        """提取出版日期"""
        # 尝试从多个位置提取日期
        pub_date_elem = soup.find('pub-date')
        if pub_date_elem:
            year = pub_date_elem.find('year')
            month = pub_date_elem.find('month')
            day = pub_date_elem.find('day')
            
            date_parts = []
            if year:
                date_parts.append(year.text.strip())
            if month:
                date_parts.append(month.text.strip())
            if day:
                date_parts.append(day.text.strip())
                
            if date_parts:
                return "-".join(date_parts)
        
        # 尝试从元数据中提取
        pub_date_meta = soup.find('meta', attrs={'name': 'citation_publication_date'})
        if pub_date_meta and pub_date_meta.get('content'):
            return pub_date_meta.get('content').strip()
            
        return None
    
    def _extract_authors(self, soup):
        """提取文章作者"""
        authors = []
        
        # 尝试从contrib-group提取
        contrib_group = soup.find('contrib-group')
        if contrib_group:
            for contrib in contrib_group.find_all('contrib', attrs={'contrib-type': 'author'}):
                author = {}
                
                # 提取姓名
                surname = contrib.find('surname')
                given_names = contrib.find('given-names')
                
                if surname and given_names:
                    author['name'] = f"{given_names.text.strip()} {surname.text.strip()}"
                elif surname:
                    author['name'] = surname.text.strip()
                
                # 提取隶属机构
                affiliation = contrib.find('aff')
                if affiliation:
                    author['affiliation'] = affiliation.text.strip()
                
                # 提取邮箱
                email = contrib.find('email')
                if email:
                    author['email'] = email.text.strip()
                
                if author:
                    authors.append(author)
        
        # 如果上面的方法没有找到作者，尝试从元数据中提取
        if not authors:
            author_metas = soup.find_all('meta', attrs={'name': 'citation_author'})
            for author_meta in author_metas:
                if author_meta.get('content'):
                    authors.append({'name': author_meta.get('content').strip()})
        
        return authors
    
    def _extract_h2_sections(self, soup):
        """
        提取文章内容中所有h2标题和相关内容
        特别关注class="pmc_sec_title"的h2标题
        """
        sections = []
        
        # 找到文档主体
        body = soup.find('body') or soup
        
        # 首先尝试查找带有特定class的h2标题
        target_h2_titles = body.find_all('h2', class_='pmc_sec_title')
        
        # 如果没有找到带特定class的h2，则尝试获取所有h2
        if not target_h2_titles:
            target_h2_titles = body.find_all('h2')
        
        if target_h2_titles:
            self.logger.info(f"找到 {len(target_h2_titles)} 个h2标题")
            for h2 in target_h2_titles:
                section_content = self._extract_section_from_h2(h2)
                if section_content:
                    sections.append(section_content)
        else:
            self.logger.warning("未找到任何h2标题")
            
            # 如果没找到h2标题，尝试寻找其他可能的章节结构
            div_sections = body.find_all('div', class_=['sec', 'section'])
            if div_sections:
                self.logger.info(f"尝试从div.sec/section中提取，找到 {len(div_sections)} 个")
                for div in div_sections:
                    # 查找div内的标题元素
                    title_elem = div.find(['h2', 'h3', 'div', 'p'], class_=['title', 'header'])
                    if not title_elem:
                        continue
                        
                    title = title_elem.text.strip()
                    if not title:
                        continue
                        
                    # 提取内容
                        content = []
                    for p in div.find_all('p'):
                        text = p.text.strip()
                        if text:
                            content.append(text)
                        if content:
                            sections.append({
                                    'title': title,
                                    'content': content
                            })
        
        self.logger.info(f"总共提取了 {len(sections)} 个章节")
        return sections
    
    def _extract_section_from_h2(self, h2_elem):
        """从h2标题提取章节内容"""
        title = h2_elem.text.strip()
        if not title:
            return None
            
        self.logger.info(f"从h2提取章节: {title}")
        
        # 收集该章节的内容，直到下一个h2或文章结束
        content = []
        current = h2_elem.next_sibling
        
        while current and current.name != 'h2':
            if current.name == 'p':
                text = current.text.strip()
                if text:
                    content.append(text)
            elif hasattr(current, 'find_all'):
                # 提取子元素中的段落
                for p in current.find_all('p'):
                    text = p.text.strip()
                    if text:
                        content.append(text)
                        
            current = current.next_sibling
        
        # 创建章节数据，只包含标题和内容
        section_data = {
            'title': title,
            'content': content
        }
            
        return section_data
