import { _decorator, Component, Node, Sprite, UITransform, JsonAsset, SpriteFrame, Canvas, ResolutionPolicy, Button } from 'cc';

const { ccclass, property, executeInEditMode } = _decorator;

/**
 * PSD to Cocos 编辑器扩展
 * 
 * 使用方法：
 * 1. 将此脚本放到 assets/scripts/editor/
 * 2. 在场景中创建空节点，添加此组件
 * 3. 拖入 cocos_layout.json
 * 4. 点击 Import To Scene
 * 
 * 如果自动加载图片失败：
 * - 展开 Auto Load Sprite Frames 列表
 * - 将所有图片的 SpriteFrame 拖入列表中
 * - 脚本会按名称自动匹配
 */

@ccclass('PSDImporter')
@executeInEditMode
export class PSDImporter extends Component {
    
    @property({ type: JsonAsset, tooltip: '拖入 cocos_layout.json' })
    layoutJson: JsonAsset = null;
    
    @property({ 
        tooltip: '图片文件夹路径（相对 assets）。留空则自动推断：新版结构使用 psd-output/{normalized_name}/images，旧版使用 psd-output/images',
        displayName: 'Images Path (Optional)'
    })
    imagesPath: string = '';

    @property({
        tooltip: '是否自动推断图片路径',
        readonly: true,
        displayName: 'Auto Inferred Path'
    })
    get autoInferredPath(): string {
        return this.inferImagesPath();
    }

    @property({ 
        tooltip: '自动加载图片（如果失败，请手动拖入下方列表）',
        displayName: 'Auto Load Images'
    })
    autoLoadImages: boolean = true;
    
    @property({ 
        type: [SpriteFrame],
        tooltip: '手动拖入所有图片的 SpriteFrame（当自动加载失败时使用）'
    })
    spriteFrames: SpriteFrame[] = [];
    
    @property({ tooltip: '点击导入' })
    set importToScene(value: boolean) {
        if (value) this.onImportToScene();
    }
    get importToScene(): boolean {
        return false;
    }
    
    @property({ tooltip: '显示详细日志' })
    verbose: boolean = true;

    @property({ 
        tooltip: '自动配置 Canvas 适配（确保场景根节点有 Canvas 组件）',
        displayName: 'Auto Config Canvas'
    })
    autoConfigCanvas: boolean = true;

    @property({ 
        tooltip: '适配策略: Fit Width = 固定宽度, Fit Height = 固定高度, Show All = 完整显示',
        type: ResolutionPolicy,
        visible(this: PSDImporter) { return this.autoConfigCanvas; }
    })
    resolutionPolicy: ResolutionPolicy = ResolutionPolicy.FIXED_WIDTH;

    @property({ 
        tooltip: '如果子元素有切图，则跳过父元素切图（避免重复渲染）',
        displayName: 'Skip Parent Slice When Children Have'
    })
    skipParentSliceWhenChildrenHave: boolean = true;

    // 创建名称到 SpriteFrame 的映射
    private spriteFrameMap: Map<string, SpriteFrame> = new Map();

    /**
     * 检测目录结构版本
     * 新版: cocos_layout.json 中包含 metadata.normalized_name
     * 旧版: 不包含该字段，使用固定路径
     */
    private detectStructureVersion(): 'new' | 'old' {
        if (!this.layoutJson) {
            return 'old';
        }

        const data = this.layoutJson.json;
        if (data?.metadata?.normalized_name) {
            return 'new';
        }
        return 'old';
    }

    /**
     * 自动推断图片路径
     * 新版: psd-output/{normalized_name}/images
     * 旧版: psd-output/images
     */
    private inferImagesPath(): string {
        const version = this.detectStructureVersion();

        if (version === 'new') {
            const data = this.layoutJson.json;
            const normalizedName = data.metadata.normalized_name;
            return `psd-output/${normalizedName}/images`;
        }

        // 旧版默认路径（向后兼容）
        return 'psd-output/images';
    }

    /**
     * 获取实际使用的图片路径
     * 如果用户手动设置了路径，则使用用户设置；否则自动推断
     */
    private getEffectiveImagesPath(): string {
        // 如果用户手动设置了路径（非空），则使用用户设置
        if (this.imagesPath && this.imagesPath.trim() !== '') {
            return this.imagesPath.trim();
        }
        // 否则自动推断
        return this.inferImagesPath();
    }

    onImportToScene() {
        if (!this.layoutJson) {
            console.error('[PSDImporter] ❌ 请先拖入 cocos_layout.json');
            return;
        }

        const data = this.layoutJson.json;
        if (!data || !data.elements) {
            console.error('[PSDImporter] ❌ JSON 格式错误');
            return;
        }

        // 检测目录结构并自动推断图片路径
        const structureVersion = this.detectStructureVersion();
        const effectiveImagesPath = this.getEffectiveImagesPath();

        if (this.verbose) {
            console.log(`[PSDImporter] 📁 检测到${structureVersion === 'new' ? '新版' : '旧版'}目录结构`);
            console.log(`[PSDImporter] 📂 图片路径: ${effectiveImagesPath}`);
            if (this.imagesPath && this.imagesPath.trim() !== '') {
                console.log(`[PSDImporter] ℹ️ 使用用户手动设置的路径`);
            } else if (structureVersion === 'new') {
                console.log(`[PSDImporter] ℹ️ 自动推断: metadata.normalized_name = "${data.metadata.normalized_name}"`);
            }
        }

        // 建立 SpriteFrame 映射
        this.buildSpriteFrameMap();
        
        const totalElements = this.countTotalElements(data.elements);
        console.log(`\n[PSDImporter] 🚀 开始导入 ${totalElements} 个元素（${data.elements.length} 个顶层）...`);
        if (this.spriteFrameMap.size > 0) {
            console.log(`[PSDImporter] ✓ 已手动加载 ${this.spriteFrameMap.size} 个 SpriteFrame`);
        } else if (this.autoLoadImages) {
            console.log('[PSDImporter] ℹ️ 将尝试自动加载图片（如果失败请手动拖入 SpriteFrames 列表）');
        }
        
        // 创建根节点
        const normalizedName = data.metadata?.normalized_name || 'Import';
        const rootNodeName = `PSD_${normalizedName}`;
        const rootNode = new Node(rootNodeName);
        this.node.addChild(rootNode);
        
        let successCount = 0;
        let failCount = 0;
        
        // 同步创建所有节点
        data.elements.forEach((element: any) => {
            const result = this.createSpriteNode(element, rootNode);
            successCount += result.success;
            failCount += result.failed;
        });

        console.log(`\n[PSDImporter] ✅ 导入完成！`);
        console.log(`   成功: ${successCount} 个`);
        console.log(`   失败: ${failCount} 个`);
        console.log(`   顶层: ${data.elements.length} 个组/元素`);
        if (successCount > data.elements.length) {
            console.log(`   子元素: ${successCount - data.elements.length} 个`);
        }
        console.log(`   图片路径: ${effectiveImagesPath}`);
        
        // 配置 Canvas 适配
        if (this.autoConfigCanvas) {
            this.configureCanvas(data.metadata?.canvas_size);
        }
        
        if (failCount > 0 && this.spriteFrameMap.size === 0) {
            console.log('\n💡 如果图片未显示，请：');
            console.log(`   当前图片路径: ${effectiveImagesPath}`);
            if (!this.imagesPath || this.imagesPath.trim() === '') {
                console.log('   路径为自动推断，如需手动指定，请在 "Images Path" 字段中输入');
            }
            console.log('   1. 在资源管理器中找到所有图片');
            console.log('   2. 选中所有图片，拖入此组件的 "Sprite Frames" 列表');
            console.log('   3. 再次点击 Import To Scene\n');
        }
    }
    
    private configureCanvas(canvasSize: number[] | undefined) {
        try {
            // 查找场景中的 Canvas 组件
            let canvas = this.node.getComponent(Canvas);
            
            // 如果当前节点没有 Canvas，尝试向上查找
            if (!canvas && this.node.parent) {
                canvas = this.node.parent.getComponent(Canvas);
            }
            
            if (!canvas) {
                console.warn('[PSDImporter] ⚠️ 未找到 Canvas 组件，无法配置屏幕适配');
                console.log('   建议：将 PSD 导入节点拖到 Canvas 节点下，或在场景根节点添加 Canvas 组件');
                return;
            }
            
            // 设置设计分辨率
            const designWidth = canvasSize?.[0] || 1920;
            const designHeight = canvasSize?.[1] || 1080;
            
            // 应用适配策略
            switch (this.resolutionPolicy) {
                case ResolutionPolicy.FIXED_WIDTH:
                    canvas.fitWidth = true;
                    canvas.fitHeight = false;
                    break;
                case ResolutionPolicy.FIXED_HEIGHT:
                    canvas.fitWidth = false;
                    canvas.fitHeight = true;
                    break;
                case ResolutionPolicy.SHOW_ALL:
                    canvas.fitWidth = true;
                    canvas.fitHeight = true;
                    break;
                default:
                    canvas.fitWidth = true;
                    canvas.fitHeight = false;
            }
            
            console.log(`[PSDImporter] ✓ Canvas 适配已配置`);
            console.log(`   设计分辨率: ${designWidth}×${designHeight}`);
            console.log(`   适配策略: ${this.getPolicyName(this.resolutionPolicy)}`);
            console.log(`   Fit Width: ${canvas.fitWidth}, Fit Height: ${canvas.fitHeight}`);
            
        } catch (error) {
            console.error('[PSDImporter] ❌ 配置 Canvas 失败:', error);
        }
    }
    
    private getPolicyName(policy: ResolutionPolicy): string {
        const names: Record<number, string> = {
            [ResolutionPolicy.EXACT_FIT]: '精确适配 (EXACT_FIT)',
            [ResolutionPolicy.NO_BORDER]: '无边框 (NO_BORDER)',
            [ResolutionPolicy.SHOW_ALL]: '完整显示 (SHOW_ALL)',
            [ResolutionPolicy.FIXED_HEIGHT]: '固定高度 (FIXED_HEIGHT)',
            [ResolutionPolicy.FIXED_WIDTH]: '固定宽度 (FIXED_WIDTH)',
        };
        return names[policy] || '未知';
    }
    
    private buildSpriteFrameMap() {
        this.spriteFrameMap.clear();
        
        // 从手动列表建立映射
        this.spriteFrames.forEach((sf, index) => {
            if (sf && sf.name) {
                this.spriteFrameMap.set(sf.name, sf);
                // 也存储不带扩展名的版本
                const nameWithoutExt = sf.name.replace('.png', '').replace('.jpg', '');
                this.spriteFrameMap.set(nameWithoutExt, sf);
            }
        });
        
        if (this.verbose && this.spriteFrameMap.size > 0) {
            console.log('[PSDImporter] SpriteFrame 映射:');
            this.spriteFrameMap.forEach((sf, name) => {
                console.log(`   - ${name}`);
            });
        }
    }
    
    private countTotalElements(elementList: any[]): number {
        let count = 0;
        for (const elem of elementList) {
            count++;
            if (elem.children && Array.isArray(elem.children)) {
                count += this.countTotalElements(elem.children);
            }
        }
        return count;
    }

    private hasChildWithImage(elementData: any): boolean {
        if (!elementData.children || !Array.isArray(elementData.children)) {
            return false;
        }

        for (const child of elementData.children) {
            if (child.image_file) {
                return true;
            }
            if (this.hasChildWithImage(child)) {
                return true;
            }
        }

        return false;
    }

    private createSpriteNode(elementData: any, parent: Node): { success: number; failed: number } {
        try {
            let success = 0;
            let failed = 0;
            const nodeName = elementData.name || `element_${Date.now()}`;
            const node = new Node(nodeName);

            const uiTransform = node.addComponent(UITransform);

            if (elementData.cocos_position) {
                node.setPosition(
                    elementData.cocos_position.x,
                    elementData.cocos_position.y,
                    0
                );
            }

            if (elementData.cocos_size) {
                uiTransform.setContentSize(
                    elementData.cocos_size.width,
                    elementData.cocos_size.height
                );
            }

            uiTransform.anchorX = elementData.cocos_anchor?.x ?? 0.5;
            uiTransform.anchorY = elementData.cocos_anchor?.y ?? 0.5;

            parent.addChild(node);

            // 根据类型创建组件
            const type = elementData.type || 'sprite';

            // 检测是否应该跳过父元素切图
            const shouldSkipParentSlice = this.skipParentSliceWhenChildrenHave &&
                                          elementData.image_file &&
                                          this.hasChildWithImage(elementData);

            if (type === 'button') {
                // Button 类型：创建 Sprite + Button
                const sprite = node.addComponent(Sprite);
                sprite.sizeMode = Sprite.SizeMode.CUSTOM;
                sprite.color.set(255, 255, 255, 255);

                // 尝试设置 SpriteFrame
                if (elementData.image_file) {
                    this.setSpriteFrame(elementData, sprite, nodeName);
                }

                // 创建 Button 组件
                const button = node.addComponent(Button);
                button.target = node;
                button.interactable = true;

                // 应用 button_config
                const config = elementData.button_config;
                if (config) {
                    switch (config.transition) {
                        case 'scale':
                            button.transition = Button.Transition.SCALE;
                            button.zoomScale = config.zoom_scale || 0.9;
                            button.duration = config.duration || 0.1;
                            break;
                        default:
                            button.transition = Button.Transition.NONE;
                    }
                } else {
                    button.transition = Button.Transition.NONE;
                }

                if (this.verbose) {
                    console.log(`[PSDImporter] ✓ ${nodeName} (Button)`);
                }
            } else if (type === 'node') {
                // Node 类型：可选创建 Sprite（如果有图片且不应跳过）
                if (elementData.image_file && !shouldSkipParentSlice) {
                    const sprite = node.addComponent(Sprite);
                    sprite.sizeMode = Sprite.SizeMode.CUSTOM;
                    sprite.color.set(255, 255, 255, 255);
                    this.setSpriteFrame(elementData, sprite, nodeName);
                }

                if (this.verbose) {
                    if (shouldSkipParentSlice) {
                        console.log(`[PSDImporter] ✓ ${nodeName} (Node - parent slice skipped)`);
                    } else {
                        console.log(`[PSDImporter] ✓ ${nodeName} (Node)`);
                    }
                }
            } else {
                // Sprite 类型（默认）
                const sprite = node.addComponent(Sprite);
                sprite.sizeMode = Sprite.SizeMode.CUSTOM;
                sprite.color.set(255, 255, 255, 255);

                if (elementData.image_file && !shouldSkipParentSlice) {
                    this.setSpriteFrame(elementData, sprite, nodeName);
                }

                if (this.verbose) {
                    if (shouldSkipParentSlice) {
                        console.log(`[PSDImporter] ✓ ${nodeName} (Sprite - parent slice skipped)`);
                    } else {
                        console.log(`[PSDImporter] ✓ ${nodeName} (Sprite)`);
                    }
                }
            }

            if (elementData.children && Array.isArray(elementData.children) && elementData.children.length > 0) {
                if (this.verbose) {
                    console.log(`[PSDImporter]  ${nodeName} 包含 ${elementData.children.length} 个子元素`);
                }
                
                elementData.children.forEach((child: any) => {
                    const result = this.createSpriteNode(child, node);
                    success += result.success;
                    failed += result.failed;
                });
            }

            success = 1;
            return { success, failed };
        } catch (error) {
            console.error(`[PSDImporter] 创建节点 ${elementData.name} 失败:`, error);
            return { success: 0, failed: 1 };
        }
    }
    
    private setSpriteFrame(elementData: any, sprite: Sprite, nodeName: string) {
        const fileName = elementData.image_file.replace('.png', '').split('/').pop();
        if (!fileName) return;
        
        // 方法1: 从手动映射查找（最可靠）
        const manualSf = this.spriteFrameMap.get(fileName) || 
                        this.spriteFrameMap.get(nodeName);
        
        if (manualSf) {
            sprite.spriteFrame = manualSf;
            sprite.markForUpdateRenderData();
            if (this.verbose) {
                console.log(`[PSDImporter] ✓ ${nodeName} (手动映射)`);
            }
            return;
        }
        
        // 方法2: 尝试自动加载（编辑器模式可能失败）
        if (this.autoLoadImages && this.spriteFrameMap.size === 0) {
            // 延迟一帧尝试加载
            this.scheduleOnce(() => {
                if (!sprite || !sprite.isValid) return;
                
                // 尝试通过名称查找资源
                const sf = this.findSpriteFrameByName(fileName);
                if (sf) {
                    sprite.spriteFrame = sf;
                    sprite.markForUpdateRenderData();
                    if (this.verbose) {
                        console.log(`[PSDImporter] ✓ ${nodeName} (自动查找)`);
                    }
                } else {
                    console.warn(`[PSDImporter] ⚠️ ${nodeName}: 未找到 SpriteFrame`);
                    console.warn(`   请将图片拖入 "Sprite Frames" 列表后重试`);
                }
            }, 0);
        }
    }
    
    private findSpriteFrameByName(name: string): SpriteFrame | null {
        // 在手动列表中查找
        for (const sf of this.spriteFrames) {
            if (sf && (sf.name === name || sf.name === name + '.png')) {
                return sf;
            }
        }
        return null;
    }
}
