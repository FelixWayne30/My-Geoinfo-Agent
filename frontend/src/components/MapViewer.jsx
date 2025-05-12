// frontend/src/components/MapViewer.jsx
import React, { useEffect, useRef } from 'react';

const MapViewer = ({ mapData }) => {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef([]);
  const polylinesRef = useRef([]);

  useEffect(() => {
    console.log("MapViewer接收的数据:", mapData);

    // 清理函数
    const cleanup = () => {
      if (mapInstanceRef.current) {
        // 清除所有标记和线条
        if (markersRef.current.length > 0) {
          mapInstanceRef.current.remove(markersRef.current);
          markersRef.current = [];
        }
        if (polylinesRef.current.length > 0) {
          mapInstanceRef.current.remove(polylinesRef.current);
          polylinesRef.current = [];
        }
      }
    };

    // 如果没有有效数据则直接返回
    if (!mapData || !mapData.success || !mapContainerRef.current) {
      cleanup();
      return;
    }

    // 加载高德地图SDK
    const loadAMapScript = () => {
      return new Promise((resolve, reject) => {
        if (window.AMap) {
          resolve();
          return;
        }

        // 防止重复加载
        if (document.querySelector('script[src*="webapi.amap.com/maps"]')) {
          // 等待已有脚本加载完成
          const checkAMap = setInterval(() => {
            if (window.AMap) {
              clearInterval(checkAMap);
              resolve();
            }
          }, 100);
          return;
        }

        const script = document.createElement('script');
        script.src = `https://webapi.amap.com/maps?v=2.0&key=${mapData.mapKey}`;
        script.async = true;
        script.onload = () => resolve();
        script.onerror = (e) => reject(e);
        document.head.appendChild(script);
      });
    };

    const loadPlugins = () => {
      return new Promise((resolve) => {
        if (!window.AMap) {
          resolve(false);
          return;
        }

        window.AMap.plugin([
          'AMap.Scale',
          'AMap.ToolBar',
          'AMap.Driving'
        ], () => {
          resolve(true);
        });
      });
    };

    const initMap = async () => {
      try {
        await loadAMapScript();
        await loadPlugins();

        // 清理旧内容
        cleanup();

        // 检查DOM元素是否存在
        if (!mapContainerRef.current) return;

        // 如果已有地图实例，则不重新创建
        if (!mapInstanceRef.current) {
          mapInstanceRef.current = new window.AMap.Map(mapContainerRef.current, {
            zoom: 13,
            resizeEnable: true,
            viewMode: '2D'
          });

          // 添加控件
          mapInstanceRef.current.addControl(new window.AMap.Scale());
          mapInstanceRef.current.addControl(new window.AMap.ToolBar());
        }

        // 渲染内容
        renderMapContent();
      } catch (error) {
        console.error("地图初始化错误:", error);
      }
    };

    const renderMapContent = () => {
      const map = mapInstanceRef.current;
      if (!map || !mapData.points || mapData.points.length === 0) return;

      const points = mapData.points;
      const newMarkers = [];
      const bounds = new window.AMap.Bounds();

      // 添加标记点 - 使用官方图标
      points.forEach((point, index) => {
        if (!point.lnglat || point.lnglat.length !== 2) {
          console.warn(`无效的坐标点:`, point);
          return;
        }

        const [lng, lat] = point.lnglat;
        const position = new window.AMap.LngLat(lng, lat);

        // 根据点类型选择不同颜色图标
        let iconUrl = '';
        if (point.type === '起点') {
          iconUrl = 'https://webapi.amap.com/theme/v1.3/markers/n/mark_r.png';
        } else if (point.type === '终点') {
          iconUrl = 'https://webapi.amap.com/theme/v1.3/markers/n/mark_r.png';
        } else {
          iconUrl = 'https://webapi.amap.com/theme/v1.3/markers/n/mark_r.png';
        }

        // 创建图标对象
        const icon = new window.AMap.Icon({
          size: new window.AMap.Size(25, 34),
          image: iconUrl,
          imageSize: new window.AMap.Size(25, 34)
        });

        // 创建标记
        const marker = new window.AMap.Marker({
          position,
          title: point.name,
          icon: icon,
          label: {
            content: `<div style="padding: 2px 5px; background-color: white; border-radius: 2px; border: 1px solid #ccc; font-size: 12px;">${String.fromCharCode(65 + index)}: ${point.name}</div>`,
            direction: 'top',
            offset: new window.AMap.Pixel(3, -35)
          },
          offset: new window.AMap.Pixel(-13, -34),
          zIndex: 101,
          map
        });

        newMarkers.push(marker);
        bounds.extend(position);
      });

      // 保存标记引用
      markersRef.current = newMarkers;

      // 如果有路径规划数据，绘制路线
      if (mapData.routeData && mapData.routeData.route && mapData.routeData.route.paths) {
        const paths = mapData.routeData.route.paths;
        if (paths.length > 0 && paths[0].steps) {
          const newPolylines = [];

          paths[0].steps.forEach(step => {
            if (step.polyline) {
              try {
                const pointsArray = step.polyline.split(';').map(p => {
                  const [lng, lat] = p.split(',').map(Number);
                  return [lng, lat];
                });

                if (pointsArray.length > 1) {
                  const polyline = new window.AMap.Polyline({
                    path: pointsArray,
                    strokeColor: '#3366FF',
                    strokeWeight: 6,
                    strokeOpacity: 0.8,
                    zIndex: 50,
                    map
                  });

                  newPolylines.push(polyline);

                  // 扩展边界包含路线
                  pointsArray.forEach(p => {
                    bounds.extend(new window.AMap.LngLat(p[0], p[1]));
                  });
                }
              } catch (e) {
                console.error('绘制路线段错误:', e);
              }
            }
          });

          // 保存路线引用
          polylinesRef.current = newPolylines;
        }
      }

      // 调整地图视野 - 延迟执行以确保地图已完全加载
      setTimeout(() => {
        try {
          // 检查边界是否有效
          if (bounds.getNorthEast() && bounds.getSouthWest()) {
            // 设置适当的缩放级别和中心点
            map.setBounds(bounds, [60, 60, 60, 60]);

            // 确保不会缩放过大或过小
            const zoom = map.getZoom();
            if (zoom > 17) map.setZoom(17);
            if (zoom < 9) map.setZoom(9);

            // 确保地图中心是路线中心
            const center = bounds.getCenter();
            map.setCenter(center);

            console.log("地图已调整至路线中心，缩放级别:", map.getZoom());
          } else {
            // 如果边界无效，则使用第一个点作为中心
            if (points.length > 0) {
              const [lng, lat] = points[0].lnglat;
              map.setCenter(new window.AMap.LngLat(lng, lat));
              map.setZoom(13);
            }
          }
        } catch (e) {
          console.error("调整地图视野错误:", e);
        }
      }, 200);
    };

    initMap();

    // 组件卸载时清理
    return cleanup;
  }, [mapData]);

  return (
    <div
      ref={mapContainerRef}
      style={{
        width: '100%',
        height: '500px',
        borderRadius: '8px',
        border: '1px solid #eee'
      }}
    />
  );
};

export default MapViewer;