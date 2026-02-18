/**
 * 简单组件 - Simple
 * 
 * 测试用例：简单组件，包含 2-3 个 JSX 元素
 * 用途：测试基础解析功能
 */

import React from 'react';
import styles from './index.module.css';

const Simple = ({ className = '', children }) => {
  return (
    <div className={styles["container"]}>
      <span className={styles["text"]}>Hello World</span>
      {children}
    </div>
  );
};

export default Simple;
