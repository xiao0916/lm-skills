/**
 * 中等复杂度组件 - Medium
 * 
 * 测试用例：中等复杂度组件，包含约 10 个 JSX 元素
 * 用途：测试中等规模组件的解析和分析功能
 */

import React from 'react';
import styles from './index.module.css';

const Medium = ({ title, description, onClick }) => {
  return (
    <div className={styles["page"]}>
      <header className={styles["header"]}>
        <div className={styles["logo"]} />
        <nav className={styles["nav"]}>
          <a className={styles["nav-link"]}>首页</a>
          <a className={styles["nav-link"]}>关于</a>
        </nav>
      </header>
      <main className={styles["content"]}>
        <div className={styles["card"]}>
          <h2 className={styles["title"]}>{title}</h2>
          <p className={styles["description"]}>{description}</p>
          <button className={styles["btn-primary"]} onClick={onClick}>
            点击
          </button>
        </div>
      </main>
      <footer className={styles["footer"]}>
        <p className={styles["copyright"]}>© 2024</p>
      </footer>
    </div>
  );
};

export default Medium;
