#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick Multilingual Analyzer - Using existing compiled libraries
"""

import os
import json
import time
import argparse
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional

from tree_sitter import Language, Parser
from transformers import AutoTokenizer
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')
import concurrent.futures
import multiprocessing
from typing import Any
import signal

# Global worker analyzer for process pool
WORKER_ANALYZER: Optional["QuickMultiLanguageAnalyzer"] = None

def _worker_init(model_name: str, emit_utf16: bool, target_language: str):
    global WORKER_ANALYZER
    try:
        os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
        WORKER_ANALYZER = QuickMultiLanguageAnalyzer(model_name=model_name, emit_utf16_offsets=emit_utf16, allowed_languages=[target_language])
    except Exception:
        WORKER_ANALYZER = None

def _worker_analyze_file(args: Tuple[str, str]) -> Optional[Dict[str, Any]]:
    """Top-level function for ProcessPoolExecutor to avoid pickling parser objects."""
    global WORKER_ANALYZER
    file_path_str, language = args
    file_path = Path(file_path_str)
    if WORKER_ANALYZER is None:
        return None
    try:
        # timeout support per file (Unix)
        def _timeout_handler(signum, frame):
            raise TimeoutError("per-file timeout")
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        timeout_secs = int(os.environ.get('ANALYZER_PER_FILE_TIMEOUT', '10'))
        signal.alarm(max(1, timeout_secs))

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
        if not code.strip():
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
            return None
        code_size = len(code)
        file_start_time = time.time()
        score, details = WORKER_ANALYZER.calculate_rule_level_alignment(code, language)
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
        file_analysis_time = time.time() - file_start_time
        aligned_count = sum(1 for d in details.values() if d['fully_aligned'])
        unaligned_rules_list = [
            {
                'rule_key': rk,
                'type': rd.get('type'),
                'start_byte': rd.get('start_byte'),
                'end_byte': rd.get('end_byte'),
                'start_aligned': rd.get('start_aligned'),
                'end_aligned': rd.get('end_aligned'),
                'fully_aligned': rd.get('fully_aligned'),
                'text_preview': rd.get('text_preview')
            }
            for rk, rd in details.items() if not rd.get('fully_aligned')
        ]
        return {
            'file': file_path.name,
            'path': str(file_path),
            'score': score,
            'total_rules': len(details),
            'aligned_rules': aligned_count,
            'unaligned_rules': unaligned_rules_list,
            'code_size': code_size,
            'analysis_time': file_analysis_time,
            'processing_speed': code_size / file_analysis_time if file_analysis_time > 0 else 0
        }
    except TimeoutError:
        try:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
        except Exception:
            pass
        return None
    except Exception:
        return None

class QuickMultiLanguageAnalyzer:
    """Quick Multilingual Analyzer - Using compiled libraries"""
    
    def __init__(self, model_name: str = "gpt2", emit_utf16_offsets: bool = False, allowed_languages: Optional[List[str]] = None):
        self.model_name = model_name
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.emit_utf16_offsets = emit_utf16_offsets
        self.allowed_languages = set(allowed_languages) if allowed_languages else None
        
        # Language configurations
        self.language_configs = {
            'python': {'symbol': 'python', 'extensions': ['.py']},
            'javascript': {'symbol': 'javascript', 'extensions': ['.js']},
            'typescript': {'symbol': 'typescript', 'extensions': ['.ts']},
            'java': {'symbol': 'java', 'extensions': ['.java']},
            'c': {'symbol': 'c', 'extensions': ['.c', '.h']},
            'cpp': {'symbol': 'cpp', 'extensions': ['.cpp', '.cc', '.cxx', '.hpp']},
            'csharp': {'symbol': 'c_sharp', 'extensions': ['.cs']},
            'go': {'symbol': 'go', 'extensions': ['.go']},
            'ruby': {'symbol': 'ruby', 'extensions': ['.rb']},
            'rust': {'symbol': 'rust', 'extensions': ['.rs']},
            'scala': {'symbol': 'scala', 'extensions': ['.scala']}
        }
        
        self.parsers = {}
        self.languages = {}
        self._setup_parsers()
    
    def _normalize_language_name(self, raw_language: Optional[str]) -> Optional[str]:
        """Normalize various language labels to our internal keys.

        Returns None if cannot map.
        """
        if not raw_language:
            return None
        name = str(raw_language).strip().lower()
        aliases = {
            'python': 'python', 'py': 'python',
            'javascript': 'javascript', 'js': 'javascript', 'node': 'javascript',
            'typescript': 'typescript', 'ts': 'typescript',
            'java': 'java',
            'c': 'c',
            'c++': 'cpp', 'cpp': 'cpp', 'cxx': 'cpp',
            'c#': 'csharp', 'csharp': 'csharp', 'cs': 'csharp',
            'go': 'go', 'golang': 'go',
            'ruby': 'ruby', 'rb': 'ruby',
            'rust': 'rust', 'rs': 'rust',
            'scala': 'scala'
        }
        return aliases.get(name)

    def _setup_parsers(self):
        """Set up parsers - Using existing compiled libraries"""
        # Resolve build directory relative to this script's directory for robustness
        script_dir = Path(__file__).resolve().parent
        build_dir = script_dir / 'build'
        
        if not build_dir.exists():
            print("Error: build directory does not exist")
            return
        
        print("Loading compiled language libraries...")
        
        # Try to initialize each language (respect allowed_languages if provided)
        for lang_name, config in self.language_configs.items():
            if self.allowed_languages is not None and lang_name not in self.allowed_languages:
                continue
            try:
                # Find corresponding language library file
                possible_paths = [
                    build_dir / f"languages_{lang_name}.so",
                    build_dir / f"languages.so",
                    build_dir / f"multilang_languages.so"
                ]
                
                library_path = None
                for path in possible_paths:
                    if path.exists():
                        library_path = path
                        break
                
                if not library_path:
                    print(f"✗ {lang_name} language library file does not exist")
                    continue
                
                parser = Parser()
                language = Language(str(library_path), config['symbol'])
                parser.set_language(language)
                
                self.parsers[lang_name] = parser
                self.languages[lang_name] = language
                print(f"✓ {lang_name} parser available (using {library_path.name})")
                
            except Exception as e:
                print(f"✗ {lang_name} parser unavailable: {e}")
    
    def get_available_languages(self) -> List[str]:
        """Get list of available languages"""
        return list(self.parsers.keys())
    
    def calculate_rule_level_alignment(self, code: str, language: str) -> Tuple[float, Dict]:
        """Calculate rule-level alignment score"""
        if language not in self.parsers:
            raise ValueError(f"Unsupported language: {language}")
        
        parser = self.parsers[language]
        code_bytes = code.encode('utf-8')
        
        # Parse code
        tree = parser.parse(code_bytes)
        
        # Extract rules
        def extract_rules(node, rules=None):
            if rules is None:
                rules = []
            
            if node.type and not node.type.startswith('ERROR'):
                rules.append({
                    'type': node.type,
                    'start_byte': node.start_byte,
                    'end_byte': node.end_byte,
                    'text': code_bytes[node.start_byte:node.end_byte].decode('utf-8', errors='ignore')[:50]
                })
            
            for child in node.children:
                extract_rules(child, rules)
            
            return rules
        
        rules = extract_rules(tree.root_node)
        
        # Tokenization with reliable offsets (prefer fast tokenizer offset_mapping)
        token_boundaries = []
        code_bytes = code.encode('utf-8')
        try:
            encoding = self.tokenizer(
                code,
                add_special_tokens=False,
                return_offsets_mapping=True
            )
            offsets = encoding.get('offset_mapping')
            if offsets is None:
                raise ValueError('offset_mapping not available')

            # Build char->byte mapping once
            char_to_byte = [0] * (len(code) + 1)
            bpos = 0
            for i, ch in enumerate(code):
                blen = len(ch.encode('utf-8'))
                char_to_byte[i] = bpos
                bpos += blen
            char_to_byte[len(code)] = len(code_bytes)

            token_boundaries = [
                (char_to_byte[s], char_to_byte[e])
                for (s, e) in offsets if not (s == e == 0 and False)
            ]
        except Exception:
            # Fallback: heuristic byte-search per token id (less reliable across tokenizers)
            try:
                tokens = self.tokenizer.encode(code, add_special_tokens=False)
                token_texts = [self.tokenizer.decode([token], clean_up_tokenization_spaces=False) for token in tokens]
            except Exception as e:
                print(f"Tokenization error: {e}")
                return 0.0, {}

            token_boundaries = []
            current_pos = 0
            for token_text in token_texts:
                token_bytes = token_text.encode('utf-8')
                if token_bytes.strip():
                    token_start = -1
                    for i in range(current_pos, len(code_bytes) - len(token_bytes) + 1):
                        if code_bytes[i:i+len(token_bytes)] == token_bytes:
                            token_start = i
                            break
                    if token_start != -1:
                        token_end = token_start + len(token_bytes)
                        token_boundaries.append((token_start, token_end))
                        current_pos = token_end
                    else:
                        token_boundaries.append((current_pos, min(current_pos + 1, len(code_bytes))))
                        current_pos = min(current_pos + 1, len(code_bytes))
                else:
                    token_boundaries.append((current_pos, min(current_pos + 1, len(code_bytes))))
                    current_pos = min(current_pos + 1, len(code_bytes))
        
        # Optionally build byte->UTF16 code unit index mapping (for emoji safety / external consumers)
        byte_to_utf16_index = None
        if self.emit_utf16_offsets:
            try:
                # Build mapping of byte positions to UTF-16 code unit indices
                byte_to_utf16_index = [0] * (len(code_bytes) + 1)
                byte_pos = 0
                utf16_index = 0
                for ch in code:
                    encoded = ch.encode('utf-8')
                    blen = len(encoded)
                    # surrogate pair in UTF-16 if codepoint > 0xFFFF
                    units = 2 if ord(ch) > 0xFFFF else 1
                    # Fill mapping for interior bytes of this codepoint
                    for i in range(blen):
                        byte_to_utf16_index[byte_pos + i] = utf16_index
                    # Boundary after this codepoint
                    byte_to_utf16_index[byte_pos + blen] = utf16_index + units
                    byte_pos += blen
                    utf16_index += units
            except Exception:
                byte_to_utf16_index = None

        # Calculate alignment
        aligned_rules = 0
        rule_details = {}
        
        for rule in rules:
            rule_start = rule['start_byte']
            rule_end = rule['end_byte']
            
            start_aligned = any(abs(rule_start - tb[0]) <= 1 for tb in token_boundaries)
            end_aligned = any(abs(rule_end - tb[1]) <= 1 for tb in token_boundaries)
            
            fully_aligned = start_aligned and end_aligned
            if fully_aligned:
                aligned_rules += 1
            
            rule_key = f"{rule['type']}_{rule['start_byte']}_{rule['end_byte']}"
            details_entry = {
                'type': rule['type'],
                'start_byte': rule['start_byte'],
                'end_byte': rule['end_byte'],
                'start_aligned': start_aligned,
                'end_aligned': end_aligned,
                'fully_aligned': fully_aligned,
                'text_preview': rule['text'][:50]
            }
            if byte_to_utf16_index is not None:
                sb = rule['start_byte']
                eb = rule['end_byte']
                if 0 <= sb < len(byte_to_utf16_index):
                    details_entry['start_utf16'] = byte_to_utf16_index[sb]
                if 0 <= eb <= len(byte_to_utf16_index):
                    details_entry['end_utf16'] = byte_to_utf16_index[eb]
            rule_details[rule_key] = details_entry
        
        alignment_score = (aligned_rules / len(rules) * 100) if rules else 0
        return alignment_score, rule_details
    
    def _analyze_single_file(self, args_tuple):
        """Deprecated: replaced by top-level worker function for pickling safety."""
        return _worker_analyze_file(args_tuple)

    def analyze_language_files(self, code_dir: str, language: str, flush_every: int = 0, output_dir: str = "results/multilang", workers: int = 1, per_file_timeout: int = 10, max_files: Optional[int] = None, batch_size: int = 0) -> Dict:
        """Analyze all files for a specific language.

        Supports two layouts:
        1) code_dir/<language> containing files (legacy)
        2) A flat or nested directory tree at code_dir where we recursively
           collect files by extension for the specified language.
        Also supports passing a single file path in code_dir.
        """
        if language not in self.parsers:
            print(f"Skipping unsupported language: {language}")
            return {}

        base_path = Path(code_dir)
        extensions = self.language_configs[language]['extensions']

        code_files = []

        # If a single file path is passed, check and use it directly
        if base_path.is_file():
            if any(str(base_path).endswith(ext) for ext in extensions):
                code_files = [base_path]
            else:
                print(f"Provided file does not match {language} extensions: {base_path}")
                return {}
        else:
            # Prefer legacy layout if present: code_dir/<language>
            language_dir = base_path / language
            search_root = language_dir if language_dir.exists() else base_path

            # Recursively gather files by extension from preferred root
            for ext in extensions:
                code_files.extend(search_root.rglob(f"*{ext}"))

            # Fallback: if language_dir exists but yielded no files, also scan base_path recursively
            if not code_files and language_dir.exists():
                for ext in extensions:
                    code_files.extend(base_path.rglob(f"*{ext}"))

        if not code_files:
            print(f"No {language} files found under {base_path}")
            return {}
        
        # If max_files specified, limit the total number of files to analyze
        if max_files is not None and max_files > 0:
            code_files = code_files[:max_files]

        print(f"\nAnalyzing {language.upper()} ({len(code_files)} files)")
        print("-" * 50)
        
        # If batch_size specified (>0), process in fixed-size batches (saving after each batch)
        if batch_size and batch_size > 0:
            total_results: Dict = {
                'language': language,
                'file_count': 0,
                'avg_score': 0.0,
                'total_rules': 0,
                'total_aligned': 0,
                'overall_alignment': 0.0,
                'total_code_size': 0,
                'total_analysis_time': 0.0,
                'avg_processing_speed': 0.0,
                'files': []
            }
            overall_start = time.time()
            part_idx = 0

            for start in range(0, len(code_files), batch_size):
                batch = code_files[start:start+batch_size]
                part_idx += 1

                # Reuse the core processing path but scoped to this batch
                file_results = []
                total_rules = 0
                total_aligned = 0
                total_code_size = 0
                batch_start_time = time.time()

                def process_collected_batch(batch_results):
                    nonlocal file_results, total_rules, total_aligned, total_code_size
                    for res in batch_results:
                        if not res:
                            continue
                        file_results.append(res)
                        total_rules += res['total_rules']
                        total_aligned += res['aligned_rules']
                        total_code_size += res['code_size']

                if workers and workers > 1:
                    max_workers = workers if workers > 0 else (multiprocessing.cpu_count() or 1)
                    mp_ctx = multiprocessing.get_context('spawn')
                    with concurrent.futures.ProcessPoolExecutor(
                        max_workers=max_workers,
                        mp_context=mp_ctx,
                        initializer=_worker_init,
                        initargs=(self.model_name, self.emit_utf16_offsets, language)
                    ) as ex:
                        os.environ['ANALYZER_PER_FILE_TIMEOUT'] = str(max(1, int(per_file_timeout)))
                        batch_iter = ex.map(_worker_analyze_file, ((str(p), language) for p in batch), chunksize=64)
                        buf = []
                        for res in tqdm(batch_iter, desc=f"Analyzing {language}", unit="files"):
                            buf.append(res)
                            if len(buf) >= 256:
                                process_collected_batch(buf)
                                buf = []
                        if buf:
                            process_collected_batch(buf)
                else:
                    results_local = []
                    for file_path in tqdm(batch, desc=f"Analyzing {language}", unit="files"):
                        # serial process single file
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                code = f.read()
                            if not code.strip():
                                continue
                            code_size = len(code)
                            file_start_time = time.time()
                            score, details = self.calculate_rule_level_alignment(code, language)
                            file_analysis_time = time.time() - file_start_time
                            aligned_count = sum(1 for d in details.values() if d['fully_aligned'])
                            unaligned_rules_list = [
                                {
                                    'rule_key': rk,
                                    'type': rd.get('type'),
                                    'start_byte': rd.get('start_byte'),
                                    'end_byte': rd.get('end_byte'),
                                    'start_aligned': rd.get('start_aligned'),
                                    'end_aligned': rd.get('end_aligned'),
                                    'fully_aligned': rd.get('fully_aligned'),
                                    'text_preview': rd.get('text_preview')
                                }
                                for rk, rd in details.items() if not rd.get('fully_aligned')
                            ]
                            results_local.append({
                                'file': file_path.name,
                                'path': str(file_path),
                                'score': score,
                                'total_rules': len(details),
                                'aligned_rules': aligned_count,
                                'unaligned_rules': unaligned_rules_list,
                                'code_size': code_size,
                                'analysis_time': file_analysis_time,
                                'processing_speed': code_size / file_analysis_time if file_analysis_time > 0 else 0
                            })
                        except Exception:
                            pass
                    process_collected_batch(results_local)

                # finalize batch stats and save
                batch_time = time.time() - batch_start_time
                avg_score = (sum(r['score'] for r in file_results) / len(file_results)) if file_results else 0.0
                overall_alignment = (total_aligned / total_rules * 100) if total_rules > 0 else 0
                avg_speed = total_code_size / batch_time if batch_time > 0 else 0

                language_chunk_result = {
                    'language': language,
                    'file_count': len(file_results),
                    'avg_score': avg_score,
                    'total_rules': total_rules,
                    'total_aligned': total_aligned,
                    'overall_alignment': overall_alignment,
                    'total_code_size': total_code_size,
                    'total_analysis_time': batch_time,
                    'avg_processing_speed': avg_speed,
                    'files': file_results
                }
                self._save_results({language: language_chunk_result}, [], output_dir, batch_time, suffix=f"_{language}_part_{part_idx}")

                # accumulate into overall totals
                total_results['file_count'] += language_chunk_result['file_count']
                total_results['total_rules'] += language_chunk_result['total_rules']
                total_results['total_aligned'] += language_chunk_result['total_aligned']
                total_results['total_code_size'] += language_chunk_result['total_code_size']
                total_results['total_analysis_time'] += language_chunk_result['total_analysis_time']
                total_results['files'].extend(file_results)

                # stop early if reached limited max_files
                if max_files is not None and total_results['file_count'] >= max_files:
                    break

            # finalize overall aggregates
            if total_results['file_count'] > 0:
                total_results['avg_score'] = (sum(r['score'] for r in total_results['files']) / len(total_results['files'])) if total_results['files'] else 0.0
                total_results['overall_alignment'] = (total_results['total_aligned'] / total_results['total_rules'] * 100) if total_results['total_rules'] > 0 else 0.0
                total_results['avg_processing_speed'] = total_results['total_code_size'] / total_results['total_analysis_time'] if total_results['total_analysis_time'] > 0 else 0.0
            return total_results

        # Analyze files (single run, with optional flush_every)
        file_results = []
        total_rules = 0
        total_aligned = 0
        total_code_size = 0
        start_time = time.time()
        chunk_idx = 0
        files_since_flush = 0
        chunk_start_time = time.time()
        
        # Parallel or serial processing of files
        def process_collected(batch_results):
            nonlocal file_results, total_rules, total_aligned, total_code_size, files_since_flush, chunk_idx, chunk_start_time
            for res in batch_results:
                if not res:
                    continue
                file_results.append(res)
                total_rules += res['total_rules']
                total_aligned += res['aligned_rules']
                total_code_size += res['code_size']
                files_since_flush += 1
                if flush_every and files_since_flush >= flush_every:
                    chunk_idx += 1
                    chunk_total_rules = sum(r['total_rules'] for r in file_results)
                    chunk_total_aligned = sum(r['aligned_rules'] for r in file_results)
                    chunk_total_size = sum(r['code_size'] for r in file_results)
                    chunk_total_time = time.time() - chunk_start_time
                    chunk_avg_score = sum(r['score'] for r in file_results) / len(file_results)
                    chunk_avg_speed = chunk_total_size / chunk_total_time if chunk_total_time > 0 else 0
                    language_chunk_result = {
                        'language': language,
                        'file_count': len(file_results),
                        'avg_score': chunk_avg_score,
                        'total_rules': chunk_total_rules,
                        'total_aligned': chunk_total_aligned,
                        'overall_alignment': (chunk_total_aligned / chunk_total_rules * 100) if chunk_total_rules > 0 else 0,
                        'total_code_size': chunk_total_size,
                        'total_analysis_time': chunk_total_time,
                        'avg_processing_speed': chunk_avg_speed,
                        'files': file_results
                    }
                    self._save_results({language: language_chunk_result}, [], output_dir, chunk_total_time, suffix=f"_{language}_part_{chunk_idx}")
                    file_results = []
                    files_since_flush = 0
                    chunk_start_time = time.time()

        if workers and workers > 1:
            max_workers = workers if workers > 0 else (multiprocessing.cpu_count() or 1)
            mp_ctx = multiprocessing.get_context('spawn')
            with concurrent.futures.ProcessPoolExecutor(
                max_workers=max_workers,
                mp_context=mp_ctx,
                initializer=_worker_init,
                initargs=(self.model_name, self.emit_utf16_offsets, language)
            ) as ex:
                # pass timeout to workers via env
                os.environ['ANALYZER_PER_FILE_TIMEOUT'] = str(max(1, int(per_file_timeout)))
                # map returns in order; use chunksize for throughput
                batch_iter = ex.map(_worker_analyze_file, ((str(p), language) for p in code_files), chunksize=64)
                # consume in minibatches for reduced overhead
                buf = []
                for res in tqdm(batch_iter, desc=f"Analyzing {language}", unit="files"):
                    buf.append(res)
                    if len(buf) >= 256:
                        process_collected(buf)
                        buf = []
                if buf:
                    process_collected(buf)
        else:
            results = []
            for file_path in tqdm(code_files, desc=f"Analyzing {language}", unit="files"):
                # serial path: best-effort timeout using monotonic time check
                start_t = time.time()
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        code = f.read()
                    if not code.strip():
                        continue
                    code_size = len(code)
                    file_start_time = time.time()
                    score, details = self.calculate_rule_level_alignment(code, language)
                    file_analysis_time = time.time() - file_start_time
                    aligned_count = sum(1 for d in details.values() if d['fully_aligned'])
                    unaligned_rules_list = [
                        {
                            'rule_key': rk,
                            'type': rd.get('type'),
                            'start_byte': rd.get('start_byte'),
                            'end_byte': rd.get('end_byte'),
                            'start_aligned': rd.get('start_aligned'),
                            'end_aligned': rd.get('end_aligned'),
                            'fully_aligned': rd.get('fully_aligned'),
                            'text_preview': rd.get('text_preview')
                        }
                        for rk, rd in details.items() if not rd.get('fully_aligned')
                    ]
                    results.append({
                        'file': file_path.name,
                        'path': str(file_path),
                        'score': score,
                        'total_rules': len(details),
                        'aligned_rules': aligned_count,
                        'unaligned_rules': unaligned_rules_list,
                        'code_size': code_size,
                        'analysis_time': file_analysis_time,
                        'processing_speed': code_size / file_analysis_time if file_analysis_time > 0 else 0
                    })
                except Exception:
                    pass
                finally:
                    if time.time() - start_t > per_file_timeout:
                        # skip this file if took too long
                        continue
                if len(results) >= 256:
                    process_collected(results)
                    results = []
            if results:
                process_collected(results)
        
        # Calculate total analysis time and speed
        total_time = time.time() - start_time
        avg_speed = total_code_size / total_time if total_time > 0 else 0
        
        if not file_results:
            return {}
        
        # If there are remaining unflushed files, they will be included in final stats and report
        # Calculate statistics
        avg_score = (sum(r['score'] for r in file_results) / len(file_results)) if file_results else 0.0
        overall_alignment = (total_aligned / total_rules * 100) if total_rules > 0 else 0
        
        result = {
            'language': language,
            'file_count': len(file_results),
            'avg_score': avg_score,
            'total_rules': total_rules,
            'total_aligned': total_aligned,
            'overall_alignment': overall_alignment,
            'total_code_size': total_code_size,
            'total_analysis_time': total_time,
            'avg_processing_speed': avg_speed,
            'files': file_results
        }
        
        print(f"\n{language.upper()} Analysis Summary:")
        print(f"  File count: {result['file_count']}")
        print(f"  Average score: {result['avg_score']:.2f}%")
        print(f"  Total rules: {result['total_rules']}")
        print(f"  Total aligned: {result['total_aligned']}")
        print(f"  Overall alignment rate: {result['overall_alignment']:.2f}%")
        print(f"  Total code size: {result['total_code_size']/1024:.2f} KB")
        print(f"  Total analysis time: {result['total_analysis_time']:.2f} seconds")
        print(f"  Average processing speed: {result['avg_processing_speed']/1024:.2f} KB/sec")
        
        # If any remaining unflushed files and flush_every was set, save a final chunk for remainder
        if flush_every and file_results:
            chunk_idx += 1
            chunk_total_rules = sum(r['total_rules'] for r in file_results)
            chunk_total_aligned = sum(r['aligned_rules'] for r in file_results)
            chunk_total_size = sum(r['code_size'] for r in file_results)
            chunk_total_time = time.time() - chunk_start_time
            chunk_avg_score = sum(r['score'] for r in file_results) / len(file_results)
            chunk_avg_speed = chunk_total_size / chunk_total_time if chunk_total_time > 0 else 0

            language_chunk_result = {
                'language': language,
                'file_count': len(file_results),
                'avg_score': chunk_avg_score,
                'total_rules': chunk_total_rules,
                'total_aligned': chunk_total_aligned,
                'overall_alignment': (chunk_total_aligned / chunk_total_rules * 100) if chunk_total_rules > 0 else 0,
                'total_code_size': chunk_total_size,
                'total_analysis_time': chunk_total_time,
                'avg_processing_speed': chunk_avg_speed,
                'files': file_results
            }

            self._save_results({language: language_chunk_result}, [], output_dir, chunk_total_time, suffix=f"_{language}_part_{chunk_idx}")

        return result

    def analyze_hf_dataset(
        self,
        dataset_name: str,
        split: str = "train",
        text_column: str = "content",
        dataset_config: Optional[str] = None,
        fixed_language: Optional[str] = None,
        language_field: Optional[str] = None,
        limit: Optional[int] = None,
        streaming: bool = True,
        use_auth_token: Optional[str] = None,
        output_dir: str = "results/multilang",
        flush_every: int = 0
    ) -> Dict:
        """Analyze code samples from a HuggingFace dataset.

        - If fixed_language is provided, all samples will be analyzed with that language.
        - If language_field is provided, each example can specify its language; unsupported ones are skipped.
        - Results are aggregated per language and saved using the same reporting format.
        """
        try:
            # Lazy import to avoid hard dependency if unused
            from datasets import load_dataset  # type: ignore
        except Exception as e:
            print(f"Error: datasets library not available. Please install with 'pip install datasets'. ({e})")
            return {}

        available_languages = self.get_available_languages()
        if not available_languages:
            print("Error: No available language parsers")
            return {}

        # Validate language selection strategy
        if not fixed_language and not language_field:
            print("Error: Please provide either a fixed language via --hf_language or a dataset language field via --hf_language_field")
            return {}

        normalized_fixed_language = None
        if fixed_language:
            normalized_fixed_language = self._normalize_language_name(fixed_language)
            if not normalized_fixed_language or normalized_fixed_language not in self.parsers:
                print(f"Error: Unsupported language: {fixed_language}")
                return {}

        print("=" * 80)
        print("Quick Multilingual Rule-level Alignment Score Analysis (HuggingFace Dataset)")
        print("=" * 80)
        print(f"Dataset: {dataset_name} | Split: {split} | Text column: {text_column}")
        if dataset_config:
            print(f"Dataset config: {dataset_config}")
        if normalized_fixed_language:
            print(f"Using fixed language: {normalized_fixed_language}")
        elif language_field:
            print(f"Using language field: {language_field}")

        # Load dataset
        try:
            ds_kwargs = {
                "path": dataset_name,
                "name": dataset_config,
                "split": split,
                "streaming": streaming,
            }
            if use_auth_token:
                ds_kwargs["use_auth_token"] = use_auth_token
            dataset = load_dataset(**ds_kwargs)
        except Exception as e:
            print(f"Error loading dataset: {e}")
            return {}

        # Prepare aggregation structures per language
        per_language_stats: Dict[str, Dict] = {}

        def ensure_lang_bucket(lang_key: str):
            if lang_key not in per_language_stats:
                per_language_stats[lang_key] = {
                    'language': lang_key,
                    'file_count': 0,
                    'avg_score': 0.0,  # will compute later
                    'total_rules': 0,
                    'total_aligned': 0,
                    'total_code_size': 0,
                    'total_analysis_time': 0.0,
                    'avg_processing_speed': 0.0,  # will compute later
                    'files': []
                }
        # Per-language chunking helpers
        lang_chunk_index: Dict[str, int] = {}
        lang_files_since_flush: Dict[str, int] = {}
        lang_chunk_start_time: Dict[str, float] = {}

        processed = 0
        overall_start_time = time.time()
        iterator = dataset if streaming else iter(dataset)

        try:
            pbar = tqdm(iterator, desc="Analyzing HF samples", unit="samples")
            for i, example in enumerate(pbar):
                if limit is not None and processed >= limit:
                    break

                code = example.get(text_column)
                if not code or not isinstance(code, str) or not code.strip():
                    continue

                # Determine language
                language = normalized_fixed_language
                if not language and language_field:
                    language = self._normalize_language_name(example.get(language_field))
                if not language or language not in self.parsers:
                    # Skip unsupported/unknown languages
                    continue

                ensure_lang_bucket(language)

                code_size = len(code)
                sample_start = time.time()
                score, details = self.calculate_rule_level_alignment(code, language)
                sample_time = time.time() - sample_start

                aligned_count = sum(1 for d in details.values() if d['fully_aligned'])

                # Only keep unaligned rules for dataset path as well
                rules_list = [
                    {
                        'rule_key': rk,
                        'type': rd.get('type'),
                        'start_byte': rd.get('start_byte'),
                        'end_byte': rd.get('end_byte'),
                        'start_aligned': rd.get('start_aligned'),
                        'end_aligned': rd.get('end_aligned'),
                        'fully_aligned': rd.get('fully_aligned'),
                        'text_preview': rd.get('text_preview')
                    }
                    for rk, rd in details.items() if not rd.get('fully_aligned')
                ]

                per_language_stats[language]['files'].append({
                    'file': example.get('id', f'sample_{i}'),
                    'score': score,
                    'total_rules': len(details),
                    'aligned_rules': aligned_count,
                    'unaligned_rules': rules_list,
                    'code_size': code_size,
                    'analysis_time': sample_time,
                    'processing_speed': code_size / sample_time if sample_time > 0 else 0
                })

                per_language_stats[language]['file_count'] += 1
                per_language_stats[language]['total_rules'] += len(details)
                per_language_stats[language]['total_aligned'] += aligned_count
                per_language_stats[language]['total_code_size'] += code_size
                per_language_stats[language]['total_analysis_time'] += sample_time

                processed += 1

                # Initialize chunk timers/counters
                if language not in lang_chunk_index:
                    lang_chunk_index[language] = 0
                    lang_files_since_flush[language] = 0
                    lang_chunk_start_time[language] = time.time()

                lang_files_since_flush[language] += 1

                # Flush per language if configured
                if flush_every and lang_files_since_flush[language] >= flush_every:
                    lang_chunk_index[language] += 1
                    files = per_language_stats[language]['files']
                    chunk_total_rules = sum(r['total_rules'] for r in files)
                    chunk_total_aligned = sum(r['aligned_rules'] for r in files)
                    chunk_total_size = sum(r['code_size'] for r in files)
                    chunk_total_time = time.time() - lang_chunk_start_time[language]
                    chunk_avg_score = (sum(r['score'] for r in files) / len(files)) if files else 0.0
                    chunk_avg_speed = chunk_total_size / chunk_total_time if chunk_total_time > 0 else 0

                    language_chunk_result = {
                        'language': language,
                        'file_count': len(files),
                        'avg_score': chunk_avg_score,
                        'total_rules': chunk_total_rules,
                        'total_aligned': chunk_total_aligned,
                        'overall_alignment': (chunk_total_aligned / chunk_total_rules * 100) if chunk_total_rules > 0 else 0,
                        'total_code_size': chunk_total_size,
                        'total_analysis_time': chunk_total_time,
                        'avg_processing_speed': chunk_avg_speed,
                        'files': files
                    }

                    self._save_results({language: language_chunk_result}, [], output_dir, chunk_total_time, suffix=f"_{language}_part_{lang_chunk_index[language]}")

                    # Reset per-language buffers
                    per_language_stats[language]['files'] = []
                    lang_files_since_flush[language] = 0
                    lang_chunk_start_time[language] = time.time()
        finally:
            # tqdm will close itself when pbar goes out of scope
            pass

        # Post-process aggregates and print summaries
        results: Dict[str, Dict] = {}
        for lang, stats in per_language_stats.items():
            files = stats['files']
            if not files:
                continue
            avg_score = sum(r['score'] for r in files) / len(files)
            avg_speed = stats['total_code_size'] / stats['total_analysis_time'] if stats['total_analysis_time'] > 0 else 0

            result = {
                'language': lang,
                'file_count': stats['file_count'],
                'avg_score': avg_score,
                'total_rules': stats['total_rules'],
                'total_aligned': stats['total_aligned'],
                'overall_alignment': (stats['total_aligned'] / stats['total_rules'] * 100) if stats['total_rules'] > 0 else 0,
                'total_code_size': stats['total_code_size'],
                'total_analysis_time': stats['total_analysis_time'],
                'avg_processing_speed': avg_speed,
                'files': files
            }

            print(f"\n{lang.upper()} (HF) Analysis Summary:")
            print(f"  File count: {result['file_count']}")
            print(f"  Average score: {result['avg_score']:.2f}%")
            print(f"  Total rules: {result['total_rules']}")
            print(f"  Total aligned: {result['total_aligned']}")
            print(f"  Overall alignment rate: {result['overall_alignment']:.2f}%")
            print(f"  Total code size: {result['total_code_size']/1024:.2f} KB")
            print(f"  Total analysis time: {result['total_analysis_time']:.2f} seconds")
            print(f"  Average processing speed: {result['avg_processing_speed']/1024:.2f} KB/sec")

            results[lang] = result

        overall_time = time.time() - overall_start_time

        rankings = []
        if results:
            print(f"\n{'='*60}")
            print("Language Rankings (by average score)")
            print(f"{'='*60}")
            rankings = sorted(results.items(), key=lambda x: x[1]['avg_score'], reverse=True)
            for i, (lang, result) in enumerate(rankings, 1):
                print(f"{i:2d}. {lang:<12} {result['avg_score']:6.2f}% "
                      f"(Files: {result['file_count']}, Rules: {result['total_rules']})")

            print(f"\nTotal analysis time: {overall_time:.2f} seconds")

            print(f"\n{'='*60}")
            print("Language Processing Speed Rankings (KB/sec)")
            print(f"{'='*60}")
            speed_rankings = sorted(results.items(), key=lambda x: x[1]['avg_processing_speed'], reverse=True)
            for i, (lang, result) in enumerate(speed_rankings, 1):
                print(f"{i:2d}. {lang:<12} {result['avg_processing_speed']/1024:.2f} KB/sec "
                      f"(Total size: {result['total_code_size']/1024:.2f} KB)")

        # Save results (only detailed report)
        self._save_results(results, rankings, output_dir, overall_time)
        return results
    
    def run_analysis(self, code_dir: str = "code_samples", 
                    target_languages: List[str] = None, 
                    output_dir: str = "results/multilang",
                    flush_every: int = 0,
                    workers: int = 1,
                    per_file_timeout: int = 10,
                    max_files: Optional[int] = None,
                    batch_size: int = 0) -> Dict:
        """Run analysis"""
        available_languages = self.get_available_languages()
        
        if not available_languages:
            print("Error: No available language parsers")
            return {}
        
        if target_languages is None:
            target_languages = available_languages
        else:
            target_languages = [lang for lang in target_languages if lang in available_languages]
        
        print("=" * 80)
        print("Quick Multilingual Rule-level Alignment Score Analysis")
        print("=" * 80)
        print(f"Available languages: {' '.join(available_languages)}")
        print(f"Analyzing languages: {' '.join(target_languages)}")
        
        # Record overall analysis start time
        overall_start_time = time.time()
        
        results = {}
        for language in target_languages:
            result = self.analyze_language_files(code_dir, language, flush_every=flush_every, output_dir=output_dir, workers=workers, per_file_timeout=per_file_timeout, max_files=max_files, batch_size=batch_size)
            if result:
                results[language] = result
        
        # Calculate overall analysis time
        overall_analysis_time = time.time() - overall_start_time
        
        # Generate rankings
        rankings = []
        if results:
            print(f"\n{'='*60}")
            print("Language Rankings (by average score)")
            print(f"{'='*60}")
            
            rankings = sorted(results.items(), key=lambda x: x[1]['avg_score'], reverse=True)
            for i, (lang, result) in enumerate(rankings, 1):
                print(f"{i:2d}. {lang:<12} {result['avg_score']:6.2f}% "
                      f"(Files: {result['file_count']}, Rules: {result['total_rules']})")
            
            # Display overall analysis time
            print(f"\nTotal analysis time: {overall_analysis_time:.2f} seconds")
            
            # Calculate and display processing speed ranking for each language
            print(f"\n{'='*60}")
            print("Language Processing Speed Rankings (KB/sec)")
            print(f"{'='*60}")
            
            speed_rankings = sorted(results.items(), key=lambda x: x[1]['avg_processing_speed'], reverse=True)
            for i, (lang, result) in enumerate(speed_rankings, 1):
                print(f"{i:2d}. {lang:<12} {result['avg_processing_speed']/1024:.2f} KB/sec "
                      f"(Total size: {result['total_code_size']/1024:.2f} KB)")
        
        # Save results to files (only detailed report)
        self._save_results(results, rankings, output_dir, overall_analysis_time)
        
        return results
    
    def _save_results(self, results: Dict, rankings: List, output_dir: str, overall_analysis_time: float, suffix: str = ""):
        """Save analysis results to files. Only writes detailed_analysis JSON.

        suffix: optional string to append to the detailed filename, e.g. "_python_part_1".
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save detailed results
        detailed_results = {
            'model': self.model_name,
            'timestamp': str(Path().resolve()),
            'overall_analysis_time': overall_analysis_time,
            'summary': {
                'total_languages': len(results),
                'total_files': sum(r['file_count'] for r in results.values()),
                'total_rules': sum(r['total_rules'] for r in results.values()),
                'total_aligned': sum(r['total_aligned'] for r in results.values()),
                'total_code_size': sum(r['total_code_size'] for r in results.values()),
                'avg_processing_speed': sum(r['total_code_size'] for r in results.values()) / overall_analysis_time if overall_analysis_time > 0 else 0
            },
            'languages': results,
            'rankings': []  # rankings omitted by request
        }
        
        # Save detailed report
        detailed_file = output_path / f"detailed_analysis_{self.model_name}{suffix}.json"
        with open(detailed_file, 'w', encoding='utf-8') as f:
            json.dump(detailed_results, f, ensure_ascii=False, indent=2)
        
        print(f"\n📁 Analysis results saved to:")
        print(f"  - Detailed report: {detailed_file}")

def estimate_processing_time(analyzer, language, avg_file_size, file_count):
    """Estimate time required to process a large number of files"""
    # Get current language processing speed
    print(f"\n{'='*60}")
    print(f"Large-scale Processing Time Estimation ({language})")
    print(f"{'='*60}")
    
    # Run a small test to get processing speed
    code_dir = "code_samples"
    language_dir = Path(code_dir) / language
    
    if not language_dir.exists():
        print(f"Error: {language} language directory does not exist")
        return
    
    # Find files
    extensions = analyzer.language_configs[language]['extensions']
    code_files = []
    for ext in extensions:
        code_files.extend(language_dir.glob(f"*{ext}"))
    
    if not code_files:
        print(f"Error: No {language} files found")
        return
    
    # Calculate average size of current files
    total_size = 0
    for file_path in code_files:
        total_size += file_path.stat().st_size
    
    current_avg_size = total_size / len(code_files) if code_files else 0
    
    # If no average file size provided, use current files' average size
    if avg_file_size <= 0:
        avg_file_size = current_avg_size
    
    # Run test analysis
    start_time = time.time()
    result = analyzer.analyze_language_files(code_dir, language)
    test_time = time.time() - start_time
    
    if not result:
        print(f"Error: Unable to analyze {language} files")
        return
    
    # Calculate processing speed (bytes/second)
    processing_speed = result['total_code_size'] / test_time if test_time > 0 else 0
    
    # Estimate processing time
    total_data_size = avg_file_size * file_count
    estimated_time = total_data_size / processing_speed if processing_speed > 0 else 0
    
    # Convert to more readable time format
    def format_time(seconds):
        if seconds < 60:
            return f"{seconds:.2f} seconds"
        elif seconds < 3600:
            return f"{seconds/60:.2f} minutes"
        elif seconds < 86400:
            return f"{seconds/3600:.2f} hours"
        elif seconds < 2592000:  # 30 days
            return f"{seconds/86400:.2f} days"
        elif seconds < 31536000:  # 365 days
            return f"{seconds/2592000:.2f} months"
        else:
            return f"{seconds/31536000:.2f} years"
    
    # Display estimation results
    print(f"\nEstimation Parameters:")
    print(f"  - Current average file size: {current_avg_size/1024:.2f} KB")
    print(f"  - Used average file size: {avg_file_size/1024:.2f} KB")
    print(f"  - File count: {file_count:,}")
    print(f"  - Total data size: {total_data_size/1024/1024:.2f} MB")
    print(f"  - Processing speed: {processing_speed/1024:.2f} KB/sec")
    
    print(f"\nEstimation Results:")
    print(f"  - Estimated processing time: {format_time(estimated_time)}")
    print(f"  - Average time per file: {(estimated_time/file_count)*1000:.2f} milliseconds")
    
    # Calculate estimations for different scales
    scales = [
        (100, "100 files"),
        (1000, "1,000 files"),
        (10000, "10,000 files"),
        (100000, "100,000 files"),
        (1000000, "1,000,000 files"),
        (10000000, "10,000,000 files"),
        (100000000, "100,000,000 files")
    ]
    
    print(f"\nEstimated Times for Different Scales:")
    for scale, label in scales:
        scale_time = (avg_file_size * scale) / processing_speed if processing_speed > 0 else 0
        print(f"  - {label}: {format_time(scale_time)}")

def main():
    parser = argparse.ArgumentParser(description='Quick Multilingual Analyzer')
    parser.add_argument('--language', help='Specify language')
    parser.add_argument('--all_languages', action='store_true', help='Analyze all languages')
    parser.add_argument('--code_dir', default='code_samples', help='Code directory')
    parser.add_argument('--output_dir', default='results/multilang', help='Output directory')
    parser.add_argument('--model', default='gpt2', help='Tokenizer model')
    parser.add_argument('--models', nargs='+', help='Analyze with multiple tokenizer models (space-separated)')
    parser.add_argument('--no_progress_bar', action='store_true', help='Do not display progress bar')
    parser.add_argument('--emit_utf16', action='store_true', help='Emit UTF-16 code unit offsets alongside byte offsets for rules')
    parser.add_argument('--estimate', action='store_true', help='Estimate large-scale processing time')
    parser.add_argument('--file_count', type=int, default=1000000, help='Number of files for estimation')
    parser.add_argument('--avg_file_size', type=float, default=0, help='Average file size for estimation (bytes)')
    parser.add_argument('--flush_every', type=int, default=5000, help='Write a detailed report every N files to reduce memory usage (0=disable)')
    parser.add_argument('--workers', type=int, default=1, help='Number of worker processes for parallel analysis (1 = disable)')
    parser.add_argument('--per_file_timeout', type=int, default=10, help='Per-file analysis timeout in seconds (skip files exceeding this)')
    parser.add_argument('--max_files', type=int, default=None, help='Maximum number of files to analyze (across this run)')
    parser.add_argument('--batch_size', type=int, default=0, help='Analyze files in fixed-size batches (e.g., 5000) and save after each batch')

    # HuggingFace dataset options
    parser.add_argument('--hf_dataset', type=str, help='HuggingFace dataset name (e.g., bigcode/the-stack)')
    parser.add_argument('--hf_config', type=str, default=None, help='HuggingFace dataset config name')
    parser.add_argument('--hf_split', type=str, default='train', help='Dataset split to analyze')
    parser.add_argument('--hf_text_column', type=str, default='content', help='Column containing code text')
    parser.add_argument('--hf_language', type=str, default=None, help='Fixed language to use for all samples')
    parser.add_argument('--hf_language_field', type=str, default=None, help='Field name containing per-sample language')
    parser.add_argument('--hf_limit', type=int, default=None, help='Limit number of samples to analyze')
    parser.add_argument('--hf_streaming', action='store_true', help='Enable streaming mode when loading dataset')
    parser.add_argument('--no_hf_streaming', dest='hf_streaming', action='store_false', help='Disable streaming mode')
    parser.set_defaults(hf_streaming=True)
    parser.add_argument('--hf_token', type=str, default=None, help='HuggingFace auth token (if required)')
    
    args = parser.parse_args()
    
    # If no progress bar specified, replace tqdm with no-op version
    if args.no_progress_bar:
        import builtins
        builtins.tqdm = lambda x, **kwargs: x
    
    # If estimation mode, only run once (use --model)
    if args.estimate:
        analyzer = QuickMultiLanguageAnalyzer(model_name=args.model, emit_utf16_offsets=args.emit_utf16)
        # If estimation mode, only run estimation function
        language = args.language if args.language else 'python'
        estimate_processing_time(analyzer, language, args.avg_file_size, args.file_count)
    else:
        # Normal analysis mode
        # Determine tokenizer models to run
        models_to_run = args.models if args.models and len(args.models) > 0 else [ args.model ]

        multi_model_index = {
            'models': models_to_run,
            'runs': []
        }
        # Track per-model, per-language summary for comparison
        per_model_language_summary = {}

        for mdl in models_to_run:
            print(f"\n{'='*80}")
            print(f"Running analysis with tokenizer model: {mdl}")
            print(f"{'='*80}")

            analyzer = QuickMultiLanguageAnalyzer(model_name=mdl, emit_utf16_offsets=args.emit_utf16)

            if args.hf_dataset:
                _ = analyzer.analyze_hf_dataset(
                    dataset_name=args.hf_dataset,
                    split=args.hf_split,
                    text_column=args.hf_text_column,
                    dataset_config=args.hf_config,
                    fixed_language=args.hf_language,
                    language_field=args.hf_language_field,
                    limit=args.hf_limit,
                    streaming=args.hf_streaming,
                    use_auth_token=args.hf_token,
                    output_dir=args.output_dir,
                    flush_every=args.flush_every,
                )
            else:
                if args.language:
                    target_languages = [args.language]
                elif args.all_languages:
                    target_languages = None  # Analyze all available languages
                else:
                    target_languages = ['python']  # Default to analyzing only Python

                run_results = analyzer.run_analysis(
                    args.code_dir,
                    target_languages,
                    args.output_dir,
                    flush_every=args.flush_every,
                    workers=args.workers,
                    per_file_timeout=args.per_file_timeout,
                    max_files=args.max_files,
                    batch_size=args.batch_size,
                )
                # Save simple per-language avg_score/overall_alignment for comparison
                per_model_language_summary[mdl] = {
                    lang: {
                        'avg_score': data.get('avg_score', 0.0),
                        'overall_alignment': data.get('overall_alignment', 0.0),
                        'file_count': data.get('file_count', 0)
                    }
                    for lang, data in run_results.items()
                }

            # Record per-model output file paths for convenience
            multi_model_index['runs'].append({
                'model': mdl,
                'detailed_report': str(Path(args.output_dir) / f"detailed_analysis_{mdl}.json")
            })

        # Save a small multi-model index file for downstream tools
        try:
            out_dir = Path(args.output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            index_file = out_dir / 'multi_model_summary.json'
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump(multi_model_index, f, ensure_ascii=False, indent=2)
            print(f"\n🧭 Multi-model summary index saved to: {index_file}")
        except Exception as e:
            print(f"Failed to write multi-model summary index: {e}")

        # Additionally, write a cross-model alignment comparison per language (if local files path used)
        if per_model_language_summary:
            try:
                # Build a language-centric view
                languages = set()
                for model_summary in per_model_language_summary.values():
                    languages.update(model_summary.keys())

                comparison = {
                    'languages': sorted(list(languages)),
                    'models': models_to_run,
                    'data': {
                        lang: {
                            mdl: per_model_language_summary.get(mdl, {}).get(lang, {})
                            for mdl in models_to_run
                        }
                        for lang in languages
                    }
                }

                cmp_file = Path(args.output_dir) / 'model_alignment_comparison.json'
                with open(cmp_file, 'w', encoding='utf-8') as f:
                    json.dump(comparison, f, ensure_ascii=False, indent=2)
                print(f"Alignment comparison across models saved to: {cmp_file}")
            except Exception as e:
                print(f"Failed to write model alignment comparison: {e}")

if __name__ == "__main__":
    main()