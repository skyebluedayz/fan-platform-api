export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-between p-24">
      <div className="z-10 w-full max-w-5xl items-center justify-between font-mono text-sm">
        <h1 className="text-4xl font-bold text-center mb-8">
          Fan Platform
        </h1>
        <p className="text-center text-lg mb-4">
          ファンとクリエイター向けのプラットフォーム
        </p>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-8">
          <div className="p-6 border rounded-lg">
            <h2 className="text-xl font-semibold mb-2">ファン機能</h2>
            <ul className="list-disc list-inside">
              <li>クリエイター支援</li>
              <li>サブスクリプション</li>
              <li>投げ銭機能</li>
            </ul>
          </div>
          
          <div className="p-6 border rounded-lg">
            <h2 className="text-xl font-semibold mb-2">クリエイター機能</h2>
            <ul className="list-disc list-inside">
              <li>限定コンテンツ投稿</li>
              <li>収益管理</li>
              <li>ファン管理</li>
            </ul>
          </div>
        </div>
      </div>
    </main>
  )
}
